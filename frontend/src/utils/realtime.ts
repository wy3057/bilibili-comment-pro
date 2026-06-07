import { useEffect, useState } from "react";

const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL || "ws://localhost:8000/api/ws";

export function useTenantRealtime(token: string | null, tenantId: string | null | undefined) {
  const [eventVersion, setEventVersion] = useState(0);

  useEffect(() => {
    if (!token || !tenantId) return;

    const websocket = new WebSocket(`${WS_BASE_URL}/${tenantId}?token=${encodeURIComponent(token)}`);

    websocket.onmessage = () => {
      setEventVersion((value) => value + 1);
    };

    return () => {
      websocket.close();
    };
  }, [token, tenantId]);

  return eventVersion;
}

