import express from "express";
import { chromium } from "playwright";
import crypto from "node:crypto";

const PORT = Number(process.env.HELPER_PORT || 4300);
const LOGIN_HEADLESS = process.env.PLAYWRIGHT_LOGIN_HEADLESS === "true";
const BACKGROUND_HEADLESS = process.env.PLAYWRIGHT_BACKGROUND_HEADLESS !== "false";
const SESSION_TTL_MS = Number(process.env.HELPER_SESSION_TTL_MS || 10 * 60 * 1000);
const SLOW_MO_MS = Number(process.env.PLAYWRIGHT_SLOW_MO_MS || 150);
const USER_AGENT =
  process.env.PLAYWRIGHT_USER_AGENT ||
  "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36";

const sessions = new Map();

function now() {
  return Date.now();
}

function buildCookiePairs(cookieString) {
  return String(cookieString || "")
    .split(";")
    .map((segment) => segment.trim())
    .filter(Boolean)
    .map((segment) => {
      const idx = segment.indexOf("=");
      if (idx === -1) return null;
      return {
        name: segment.slice(0, idx),
        value: segment.slice(idx + 1),
      };
    })
    .filter(Boolean);
}

function joinCookies(cookies) {
  return cookies.map((item) => `${item.name}=${item.value}`).join("; ");
}

function extractRuntime(cookies) {
  const map = Object.fromEntries(cookies.map((item) => [item.name, item.value]));
  return {
    msToken: map.msToken || "",
    s_v_web_id: map.s_v_web_id || "",
    ttwid: map.ttwid || "",
    passport_csrf_token: map.passport_csrf_token || "",
    passport_csrf_token_default: map.passport_csrf_token_default || "",
  };
}

function extractProfileFromCookies(cookies) {
  const map = Object.fromEntries(cookies.map((item) => [item.name, item.value]));
  const externalUserId = map.uid_tt || map.uid_tt_ss || map.sid_guard || map.sessionid_ss || crypto.createHash("sha1").update(joinCookies(cookies)).digest("hex");
  return {
    external_user_id: externalUserId,
    nickname: map.sso_uid_tt ? `douyin-${map.sso_uid_tt}` : `douyin-${String(externalUserId).slice(0, 8)}`,
    avatar_url: null,
  };
}

function inferAwemeId(value) {
  if (!value) return null;
  const match = String(value).match(/(?:video\/|modal_id=)(\d+)/);
  if (match) return match[1];
  if (/^\d+$/.test(String(value))) return String(value);
  return null;
}

async function prepareContext(context) {
  await context.addInitScript(() => {
    Object.defineProperty(navigator, "webdriver", {
      get: () => false,
    });
    Object.defineProperty(navigator, "platform", {
      get: () => "MacIntel",
    });
    Object.defineProperty(navigator, "languages", {
      get: () => ["zh-CN", "zh", "en-US", "en"],
    });
    Object.defineProperty(navigator, "plugins", {
      get: () => [1, 2, 3, 4, 5],
    });
    window.chrome = window.chrome || { runtime: {} };
  });
}

async function launchBrowser({ interactive = false } = {}) {
  const browser = await chromium.launch({
    headless: interactive ? LOGIN_HEADLESS : BACKGROUND_HEADLESS,
    slowMo: interactive ? SLOW_MO_MS : 0,
    ignoreDefaultArgs: ["--enable-automation"],
    args: [
      "--disable-blink-features=AutomationControlled",
      "--disable-dev-shm-usage",
      "--no-sandbox",
      "--start-maximized",
    ],
  });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 960 },
    userAgent: USER_AGENT,
    locale: "zh-CN",
    timezoneId: "Asia/Shanghai",
  });
  await prepareContext(context);
  return { browser, context };
}

async function withPage(task, options = {}) {
  const { browser, context } = await launchBrowser(options);
  const page = await context.newPage();
  try {
    return await task({ browser, context, page });
  } finally {
    await browser.close();
  }
}

async function setCookieString(context, cookieString) {
  const pairs = buildCookiePairs(cookieString);
  if (pairs.length === 0) {
    throw new Error("Cookie string is empty");
  }
  const cookies = pairs.map((item) => ({
    name: item.name,
    value: item.value,
    domain: ".douyin.com",
    path: "/",
    httpOnly: false,
    secure: true,
    sameSite: "Lax",
  }));
  await context.addCookies(cookies);
}

async function applyCookieString(context, page, cookieString, url = "https://www.douyin.com/") {
  await setCookieString(context, cookieString);
  await page.goto(url, { waitUntil: "domcontentloaded", timeout: 30000 });
  await page.waitForTimeout(1500);
}

async function takePageScreenshot(page) {
  return (await page.screenshot({ fullPage: false, type: "png" })).toString("base64");
}

async function resolvePageTitle(page) {
  return page.evaluate(() => {
    const ogTitle = document.querySelector('meta[property="og:title"]')?.getAttribute("content");
    return ogTitle || document.title || "";
  });
}

function serializeSession(session) {
  return {
    session_id: session.id,
    helper_session_id: session.id,
    status: session.status,
    login_url: session.loginUrl,
    qr_image_base64: session.qrImageBase64,
    detail: session.detail || null,
    cookie: session.cookie || null,
    runtime: session.runtime || {},
    profile: session.profile || null,
  };
}

async function createLoginSession() {
  const { browser, context } = await launchBrowser({ interactive: true });
  const page = await context.newPage();
  await page.goto("https://www.douyin.com/", { waitUntil: "domcontentloaded", timeout: 30000 });
  await page.waitForTimeout(2500);
  await page.bringToFront();
  const id = crypto.randomUUID();
  const screenshot = await takePageScreenshot(page);
  const session = {
    id,
    browser,
    context,
    page,
    createdAt: now(),
    expiresAt: now() + SESSION_TTL_MS,
    status: "pending",
    loginUrl: page.url(),
    qrImageBase64: screenshot,
    detail: null,
    cookie: null,
    runtime: {},
    profile: null,
  };
  sessions.set(id, session);
  return session;
}

async function refreshSessionState(session) {
  if (session.expiresAt < now()) {
    session.status = "expired";
    return session;
  }
  const cookies = await session.context.cookies(["https://www.douyin.com"]);
  const runtime = extractRuntime(cookies);
  const cookieString = joinCookies(cookies);
  session.loginUrl = session.page.url();
  session.qrImageBase64 = await takePageScreenshot(session.page);
  try {
    await session.page.bringToFront();
  } catch {}
  if (cookies.some((item) => item.name === "sessionid_ss")) {
    session.status = "done";
    session.cookie = cookieString;
    session.runtime = runtime;
    session.profile = extractProfileFromCookies(cookies);
  } else if (/验证|验证码|安全验证|异常/.test(await session.page.title().catch(() => ""))) {
    session.status = "verify";
    session.detail = "请在弹出的抖音浏览器窗口内手动完成验证码";
  }
  return session;
}

function getCommentItemsFromPayload(payload) {
  if (!payload || typeof payload !== "object") return [];
  if (Array.isArray(payload.comments)) return payload.comments;
  if (Array.isArray(payload.comment_list)) return payload.comment_list;
  if (payload.data && Array.isArray(payload.data.comments)) return payload.data.comments;
  if (payload.data && Array.isArray(payload.data.comment_list)) return payload.data.comment_list;
  return [];
}

async function clickCommentEntrances(page) {
  const selectors = [
    'button:has-text("评论")',
    'span:has-text("评论")',
    'div:has-text("评论")',
    'a:has-text("评论")',
    '[data-e2e*="comment"]',
    '[class*="comment"]',
  ];
  for (const selector of selectors) {
    try {
      const locator = page.locator(selector).first();
      if (await locator.count()) {
        await locator.click({ timeout: 1000, force: true });
        await page.waitForTimeout(600);
        return true;
      }
    } catch {}
  }
  try {
    const clicked = await page.evaluate(() => {
      const nodes = Array.from(document.querySelectorAll("button,span,div,a"));
      const candidate = nodes.find((node) => /评论/.test((node.textContent || "").trim()));
      if (candidate instanceof HTMLElement) {
        candidate.click();
        return true;
      }
      return false;
    });
    if (clicked) {
      await page.waitForTimeout(600);
      return true;
    }
  } catch {}
  return false;
}

async function captureCommentNetwork(page, awemeId) {
  const topLevel = [];
  const topSeen = new Set();
  const repliesByParent = new Map();
  const pending = [];
  const handler = (response) => {
    const url = response.url();
    if (!url.includes("/aweme/v1/web/comment/list")) {
      return;
    }
    pending.push(
      (async () => {
        let payload;
        try {
          payload = await response.json();
        } catch {
          return;
        }
        const comments = getCommentItemsFromPayload(payload);
        if (!comments.length) return;
        const parsedUrl = new URL(url);
        const isReply = url.includes("/reply/");
        if (isReply) {
          const parentId = parsedUrl.searchParams.get("comment_id") || parsedUrl.searchParams.get("cid");
          if (!parentId) return;
          const existing = repliesByParent.get(parentId) || [];
          for (const item of comments) {
            existing.push(item);
          }
          repliesByParent.set(parentId, existing);
          return;
        }
        for (const item of comments) {
          const commentId = String(item.comment_id || item.id || item.cid || "");
          if (!commentId || topSeen.has(commentId)) continue;
          topSeen.add(commentId);
          topLevel.push(item);
        }
      })()
    );
  };
  page.on("response", handler);
  try {
    await page.goto(`https://www.douyin.com/video/${awemeId}`, { waitUntil: "domcontentloaded", timeout: 30000 });
    await page.waitForTimeout(2500);
    await clickCommentEntrances(page);
    for (let i = 0; i < 4; i += 1) {
      await page.mouse.wheel(0, 900);
      await page.waitForTimeout(1200);
      if (topLevel.length > 0) {
        break;
      }
    }
    await page.waitForTimeout(2500);
  } finally {
    page.off("response", handler);
  }
  await Promise.allSettled(pending);
  return topLevel.map((item) => {
    const commentId = String(item.comment_id || item.id || item.cid || "");
    return {
      ...item,
      reply_comments: repliesByParent.get(commentId) || item.reply_comments || item.reply_comment || [],
    };
  });
}

async function scrapeComments(page) {
  return page.evaluate(() => {
    const rootCandidates = Array.from(
      document.querySelectorAll('[data-e2e*="comment"], [class*="comment"], [id*="comment"]')
    );
    const items = [];
    const seen = new Set();
    for (const node of rootCandidates) {
      const text = node.textContent?.trim();
      if (!text || text.length < 2) continue;
      const commentId =
        node.getAttribute("data-id") ||
        node.getAttribute("data-comment-id") ||
        node.getAttribute("data-cid") ||
        null;
      if (!commentId || seen.has(commentId)) continue;
      seen.add(commentId);
      items.push({
        comment_id: commentId,
        content: text.slice(0, 280),
        create_time: Math.floor(Date.now() / 1000),
        digg_count: 0,
        reply_comment_total: 0,
        comment_user_nickname: "Douyin User",
        user_id: commentId,
        raw_html: node.outerHTML.slice(0, 1000),
      });
    }
    return items;
  });
}

async function publishCommentByApi(page, awemeId, commentId, content) {
  return page.evaluate(
    async ({ awemeId: targetAwemeId, commentId: targetCommentId, content: replyContent }) => {
      const readCookieMap = () =>
        Object.fromEntries(
          document.cookie
            .split(";")
            .map((item) => item.trim())
            .filter(Boolean)
            .map((item) => {
              const idx = item.indexOf("=");
              return [item.slice(0, idx), item.slice(idx + 1)];
            })
        );
      const resolveWebId = () => {
        const tokenCandidates = ["__tea_cache_tokens_6383", "__tea_cache_tokens_1300", "__tea_cache_tokens_2285", "__tea_cache_tokens_7497"];
        for (const key of tokenCandidates) {
          try {
            const parsed = JSON.parse(localStorage.getItem(key) || "{}");
            if (parsed.web_id || parsed.user_unique_id) {
              return parsed.web_id || parsed.user_unique_id;
            }
          } catch {}
        }
        return "";
      };
      const buildPublishQueryParams = (cookieMap) => {
        const verifyFp = cookieMap.s_v_web_id || "";
        const uifid = cookieMap.UIFID || "";
        return new URLSearchParams({
          app_name: "aweme",
          enter_from: "discover",
          previous_page: "discover",
          device_platform: "webapp",
          aid: "6383",
          channel: "channel_pc_web",
          pc_client_type: "1",
          update_version_code: "170400",
          version_code: "17.4.0",
          version_name: "17.4.0",
          cookie_enabled: "true",
          screen_width: String(window.innerWidth || 1440),
          screen_height: String(window.innerHeight || 960),
          browser_language: navigator.language || "zh-CN",
          browser_platform: navigator.platform || "MacIntel",
          browser_name: "Chrome",
          browser_version: "125.0.0.0",
          browser_online: "true",
          engine_name: "Blink",
          engine_version: "125.0.0.0",
          os_name: "Mac OS",
          os_version: "10.15.7",
          cpu_core_num: "8",
          device_memory: "16",
          platform: "PC",
          downlink: "10",
          effective_type: "4g",
          round_trip_time: "0",
          webid: resolveWebId(),
          uifid,
          verifyFp,
          fp: verifyFp,
        });
      };

      const cookieMap = readCookieMap();
      const csrf = cookieMap.passport_csrf_token || cookieMap.passport_csrf_token_default || "";
      const params = buildPublishQueryParams(cookieMap);

      const body = new URLSearchParams({
        aweme_id: targetAwemeId,
        reply_id: targetCommentId,
        text: replyContent,
        text_extra: "[]",
        comment_send_celltime: String(Math.floor(Math.random() * 19000) + 1000),
        comment_video_celltime: String(Math.floor(Math.random() * 19000) + 1000),
      });

      const response = await fetch(`/aweme/v1/web/comment/publish/?${params.toString()}`, {
        method: "POST",
        credentials: "include",
        headers: {
          accept: "application/json, text/plain, */*",
          "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
          "x-secsdk-csrf-token": csrf,
          referer: `https://www.douyin.com/discover?modal_id=${targetAwemeId}`,
          origin: "https://www.douyin.com",
        },
        body: body.toString(),
      });
      const text = await response.text();
      let payload = null;
      try {
        payload = JSON.parse(text);
      } catch {}
      const ok = response.ok && payload && (payload.status_code === 0 || payload.comment);
      return {
        ok,
        status: response.status,
        detail:
          ok
            ? "Comment publish request succeeded"
            : `Douyin comment publish API failed: ${
                (payload && (payload.status_msg || payload.description || payload.message)) ||
                text ||
                `HTTP ${response.status}`
              }`,
        payload,
        raw_text: text,
      };
    },
    { awemeId, commentId, content }
  );
}

const app = express();
app.use(express.json({ limit: "2mb" }));

app.get("/healthz", (_req, res) => {
  res.json({ ok: true, status: "ok" });
});

app.post("/sessions/start", async (_req, res) => {
  try {
    const session = await createLoginSession();
    res.json({
      ok: true,
      session_id: session.id,
      helper_session_id: session.id,
      status: session.status,
      login_url: session.loginUrl,
      qr_image_base64: session.qrImageBase64,
    });
  } catch (error) {
    res.status(500).json({ ok: false, detail: error instanceof Error ? error.message : "Failed to start login session" });
  }
});

app.get("/sessions/:id", async (req, res) => {
  const session = sessions.get(req.params.id);
  if (!session) {
    res.status(404).json({ ok: false, detail: "Session not found" });
    return;
  }
  try {
    const refreshed = await refreshSessionState(session);
    res.json({ ok: true, ...serializeSession(refreshed) });
  } catch (error) {
    res.status(500).json({ ok: false, detail: error instanceof Error ? error.message : "Failed to refresh session" });
  }
});

app.post("/runtime/normalize", async (req, res) => {
  try {
    const payload = await withPage(async ({ context, page }) => {
      await applyCookieString(context, page, req.body.cookie);
      const cookies = await context.cookies(["https://www.douyin.com"]);
      return {
        cookie: joinCookies(cookies),
        runtime: extractRuntime(cookies),
        profile: extractProfileFromCookies(cookies),
      };
    });
    res.json({ ok: true, ...payload });
  } catch (error) {
    res.status(400).json({ ok: false, detail: error instanceof Error ? error.message : "Failed to normalize cookie" });
  }
});

app.post("/runtime/refresh", async (req, res) => {
  try {
    const payload = await withPage(async ({ context, page }) => {
      await applyCookieString(context, page, req.body.cookie);
      const cookies = await context.cookies(["https://www.douyin.com"]);
      return {
        cookie: joinCookies(cookies),
        runtime: { ...extractRuntime(cookies), ...(req.body.runtime || {}) },
        profile: extractProfileFromCookies(cookies),
      };
    });
    res.json({ ok: true, ...payload });
  } catch (error) {
    res.status(400).json({ ok: false, detail: error instanceof Error ? error.message : "Failed to refresh runtime" });
  }
});

app.post("/targets/resolve", async (req, res) => {
  try {
    const awemeId = inferAwemeId(req.body.aweme_id || req.body.video_url);
    if (!awemeId) {
      res.status(400).json({ ok: false, detail: "Unable to resolve aweme_id" });
      return;
    }
    const videoUrl = req.body.video_url || `https://www.douyin.com/video/${awemeId}`;
    const payload = await withPage(async ({ context, page }) => {
      await applyCookieString(context, page, req.body.cookie, videoUrl);
      const title = req.body.title || (await resolvePageTitle(page)) || `抖音个人作品 ${awemeId}`;
      return {
        aweme_id: awemeId,
        video_url: videoUrl,
        title,
      };
    });
    res.json({ ok: true, ...payload });
  } catch (error) {
    res.status(400).json({ ok: false, detail: error instanceof Error ? error.message : "Failed to resolve target" });
  }
});

app.post("/comments/fetch", async (req, res) => {
  try {
    const awemeId = inferAwemeId(req.body.aweme_id);
    if (!awemeId) {
      res.status(400).json({ ok: false, detail: "aweme_id is required" });
      return;
    }
    const payload = await withPage(async ({ context, page }) => {
      await setCookieString(context, req.body.cookie);
      const networkComments = await captureCommentNetwork(page, awemeId);
      if (networkComments.length > 0) {
        return {
          comments: networkComments,
          mode: "network",
        };
      }
      await page.goto(`https://www.douyin.com/video/${awemeId}`, { waitUntil: "domcontentloaded", timeout: 30000 });
      await page.waitForTimeout(2500);
      await clickCommentEntrances(page);
      await page.waitForTimeout(1200);
      return {
        comments: await scrapeComments(page),
        mode: "dom-fallback",
      };
    });
    res.json({ ok: true, ...payload });
  } catch (error) {
    res.status(400).json({ ok: false, detail: error instanceof Error ? error.message : "Failed to fetch comments" });
  }
});

app.post("/comments/reply", async (req, res) => {
  try {
    const awemeId = inferAwemeId(req.body.aweme_id);
    if (!awemeId || !req.body.comment_id || !req.body.content) {
      res.status(400).json({ ok: false, detail: "aweme_id, comment_id, and content are required" });
      return;
    }
    const payload = await withPage(async ({ context, page }) => {
      await applyCookieString(context, page, req.body.cookie, `https://www.douyin.com/video/${awemeId}`);
      await page.waitForTimeout(3500);
      return await publishCommentByApi(
        page,
        String(awemeId),
        String(req.body.comment_id),
        String(req.body.content)
      );
    });
    res.status(payload.ok ? 200 : 400).json(payload);
  } catch (error) {
    res.status(400).json({ ok: false, detail: error instanceof Error ? error.message : "Failed to send reply" });
  }
});

app.listen(PORT, () => {
  console.log(`douyin-personal-helper listening on ${PORT}`);
});
