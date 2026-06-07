# Douyin Integration

## What This Module Does

The platform now includes a parallel Douyin module for:

- Douyin app configuration storage
- importing an already-authorized Douyin account
- adding Douyin video targets by `item_id`
- polling comment lists and comment replies
- manually replying to Douyin comments

This module is intentionally isolated from the existing Bilibili module so the original workflow remains stable.

## Why The Backend Uses HTTP Instead Of The Official SDK

The referenced Douyin server SDK overview currently exposes SDK support for:

- Java
- Node.js
- Go

This project backend is Python, so the integration uses official HTTP OpenAPI calls instead of an SDK wrapper.

## Authorization Constraint

This admin system is a Web console, not a Douyin mini-app.
Because of that, it cannot directly trigger the Douyin mini-app authorization UI.

Current workflow:

1. Complete official Douyin authorization in your own mini-app environment.
2. Obtain `open_id` and `access_token`.
3. Import them into this platform from the Douyin page.

After import, the platform can use the stored token to:

- list comments
- list comment replies
- send manual replies

## Current Scope

Supported in this implementation:

- app config storage
- account token import
- account token refresh
- target creation
- manual target polling
- comment handling state
- manual reply sending
- reply action history

Not implemented in this version:

- Web-based Douyin auth initiation
- unified cross-platform analytics across Bilibili and Douyin
- fully generalized platform abstraction for all modules

## Operational Notes

- The Douyin module expects `item_id`, not a web URL.
- If token permissions are insufficient, the OpenAPI error is returned directly to the UI.
- If a refresh token is missing or invalid, re-import a fresh authorization token.
