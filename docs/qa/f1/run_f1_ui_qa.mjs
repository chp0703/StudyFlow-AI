#!/usr/bin/env node
/**
 * Automated Frontend Logic & Browser Chaos QA Runner for StudyFlow AI – Feature 1 (Planner).
 *
 * Layer 1 (Default – zero extra npm install, requires Node 22+):
 *   node docs/qa/f1/run_f1_ui_qa.mjs
 *   Runs real frontend clarification regex checks (CF-03), 8,000-char composer guardrail (CF-08),
 *   sendMessage retry check (CF-05), offline error mapping check (CF-09), and all pure-TS unit tests.
 *
 * Layer 2 (Optional Browser Chaos via Playwright against running local web app):
 *   node docs/qa/f1/run_f1_ui_qa.mjs --browser --url http://127.0.0.1:5173 --email qa@test.local --password <pass>
 */

import fs from "node:fs"
import path from "node:path"
import { spawnSync } from "node:child_process"
import { fileURLToPath, pathToFileURL } from "node:url"

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const ROOT = path.resolve(__dirname, "..", "..", "..")
const FRONTEND_DIR = path.join(ROOT, "frontend")
const REPORT_DIR = path.join(ROOT, "logs", "f1-qa-reports")

function parseArgs(argv) {
  const opts = { browser: false, url: "http://127.0.0.1:5173", email: "", password: "" }
  for (let i = 0; i < argv.length; i += 1) {
    if (argv[i] === "--browser") opts.browser = true
    else if (argv[i] === "--url" && argv[i + 1]) opts.url = argv[++i]
    else if (argv[i] === "--email" && argv[i + 1]) opts.email = argv[++i]
    else if (argv[i] === "--password" && argv[i + 1]) opts.password = argv[++i]
  }
  return opts
}

function assertLoopbackUrl(rawUrl) {
  if (rawUrl.includes("phomrutsdhdgejlskwcb")) {
    throw new Error(`[BLOCKED] Forbidden cloud project URL: ${rawUrl}`)
  }
  const u = new URL(rawUrl)
  if (!["127.0.0.1", "localhost", "::1"].includes(u.hostname)) {
    throw new Error(`[BLOCKED] --url must be loopback (127.0.0.1/localhost), got: ${rawUrl}`)
  }
}

async function runLayer1Checks() {
  const results = []

  // 1. F1-E07-01 / CF-03: Real execution of frontend/src/features/planner/clarification.ts
  const clarPath = pathToFileURL(path.join(FRONTEND_DIR, "src", "features", "planner", "clarification.ts")).href
  const { createClarificationDraft } = await import(clarPath)
  const qs = [
    { field: "estimated_minutes", message: "Thời lượng?", choices: [] },
    { field: "deadline_date", message: "Hạn?", choices: [] },
  ]
  const probes = [
    {
      input: "Học Toán 8h tối mai",
      badMinutes: "480",
      expectedDate: "2026-11-26",
      expectedTime: "20:00",
    },
    {
      input: "Nộp bài trước 12h đêm nay",
      badMinutes: "720",
      expectedDate: "2026-11-25",
      expectedTime: null,
    },
    {
      input: "Học Địa lý lúc 25h ngày mai",
      badMinutes: "1500",
      expectedDate: "2026-11-26",
      expectedTime: null,
    },
    {
      input: "Ôn Sinh lúc 10h kém 15 sáng mai",
      badMinutes: "600",
      expectedDate: "2026-11-26",
      expectedTime: "09:45",
    },
  ]
  const cf03Issues = []
  for (const p of probes) {
    const draft = createClarificationDraft(qs, p.input, "2026-11-25")
    if (draft.estimated_minutes === p.badMinutes) {
      cf03Issues.push(`"${p.input}" -> estimated_minutes=${draft.estimated_minutes} (sai giờ->phút)`)
    }
    if (p.expectedTime && draft["start_at.time"] !== p.expectedTime) {
      cf03Issues.push(`"${p.input}" -> start_at.time=${draft["start_at.time"]} (kỳ vọng ${p.expectedTime})`)
    }
    if (draft["start_at.date"] !== p.expectedDate) {
      cf03Issues.push(`"${p.input}" -> start_at.date=${draft["start_at.date"]} (kỳ vọng ${p.expectedDate})`)
    }
  }
  results.push({
    test_id: "F1-E07-01",
    priority: "P0",
    title: "Popup làm rõ không biến giờ thành phút & giữ đúng ngày/giờ [CF-03]",
    status: cf03Issues.length === 0 ? "PASS" : "BUG",
    root_cause: cf03Issues.length === 0 ? "" : "RC-FE",
    detail: cf03Issues.length === 0 ? "OK: Không biến giờ đồng hồ thành phút" : cf03Issues.slice(0, 3).join("; "),
  })

  // 2. F1-E13-02 / CF-08: ChatComposer 8,000-character limit check
  const chatComposerSrc = fs.readFileSync(
    path.join(FRONTEND_DIR, "src", "features", "assistant", "ChatComposer.tsx"),
    "utf8",
  )
  const has8kLimit = /8000|8_000|MAX_MESSAGE_LENGTH/.test(chatComposerSrc)
  results.push({
    test_id: "F1-E13-02-UI",
    priority: "P1",
    title: "ChatComposer chặn quá 8.000 ký tự khớp UserMessage contract [CF-08 / F1-B04]",
    status: has8kLimit ? "PASS" : "BUG",
    root_cause: has8kLimit ? "" : "RC-FE",
    detail: has8kLimit
      ? "OK: ChatComposer.tsx đã giới hạn 8.000 ký tự"
      : "CF-08 tái hiện: ChatComposer.tsx thiếu giới hạn 8.000 ký tự (PlannerCommandComposer có nhưng ChatComposer thiếu)",
  })

  // 3. F1-E14-02 / CF-05: sendMessage should disable blind 3x auto-retry on slow LLM 503
  const endpointsSrc = fs.readFileSync(path.join(FRONTEND_DIR, "src", "api", "endpoints.ts"), "utf8")
  const sendMsgMatch = endpointsSrc.match(/sendMessage\s*:\s*[\s\S]*?\}\),/)
  const hasNoRetry = sendMsgMatch ? /retry\s*:\s*false/.test(sendMsgMatch[0]) : false
  results.push({
    test_id: "F1-E14-02-UI",
    priority: "P1",
    title: "sendMessage tắt auto-retry mù 3 lần khi LLM timeout 503 [CF-05 / F1-B02]",
    status: hasNoRetry ? "PASS" : "BUG",
    root_cause: hasNoRetry ? "" : "RC-FE",
    detail: hasNoRetry
      ? "OK: sendMessage có retry: false"
      : "CF-05 tái hiện: endpoints.ts sendMessage thiếu retry: false nên client.ts tự bắn lặp 3 request lên LLM khi gặp 503",
  })

  // 4. F1-E11-03 / CF-09: Distinguish Offline network failure from server 503 SERVICE_UNAVAILABLE
  const clientSrc = fs.readFileSync(path.join(FRONTEND_DIR, "src", "api", "client.ts"), "utf8")
  const mapsOfflineTo503 =
    /NETWORK_ERROR[\s\S]{0,200}SERVICE_UNAVAILABLE/.test(clientSrc) ||
    /catch\s*(?:\([^)]*\))?\s*\{[\s\S]{0,240}SERVICE_UNAVAILABLE/.test(clientSrc)
  results.push({
    test_id: "F1-E11-03-UI",
    priority: "P2",
    title: "Phân biệt lỗi rớt mạng Offline với lỗi máy chủ 503 [CF-09 / Hiển TC-12]",
    status: !mapsOfflineTo503 ? "PASS" : "BUG",
    root_cause: !mapsOfflineTo503 ? "" : "RC-FE",
    detail: !mapsOfflineTo503
      ? "OK: client.ts tách riêng lỗi mất mạng Offline"
      : "CF-09 tái hiện: client.ts gộp ngoại lệ fetch (Offline) thành mã SERVICE_UNAVAILABLE giống 503",
  })

  // 5. Run pure-TS frontend unit tests (filtering out files importing 'react' if node_modules/react missing)
  const reactInstalled = fs.existsSync(path.join(FRONTEND_DIR, "node_modules", "react"))
  const testFiles = []
  function walk(dir) {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const full = path.join(dir, entry.name)
      if (entry.isDirectory()) walk(full)
      else if (entry.name.endsWith(".test.ts")) {
        if (reactInstalled || !/from\s+["']react["']/.test(fs.readFileSync(full, "utf8"))) {
          testFiles.push(full)
        }
      }
    }
  }
  walk(path.join(FRONTEND_DIR, "src"))
  const run = spawnSync(process.execPath, ["--experimental-strip-types", "--test", ...testFiles], {
    cwd: FRONTEND_DIR,
    encoding: "utf8",
  })
  const passLine = (run.stdout || "").match(/# pass (\d+)/)?.[1] ?? "0"
  const failLine = (run.stdout || "").match(/# fail (\d+)/)?.[1] ?? "0"
  results.push({
    test_id: "F1-FE-UNIT",
    priority: "P0",
    title: `Frontend Node unit tests (${testFiles.length} files${reactInstalled ? "" : ", bỏ qua file import react do chưa npm install"})`,
    status: run.status === 0 ? "PASS" : "BUG",
    root_cause: run.status === 0 ? "" : "RC-FE",
    detail: `pass=${passLine}, fail=${failLine}`,
  })

  return results
}

async function runBrowserChaos(opts) {
  assertLoopbackUrl(opts.url)
  let playwright
  try {
    playwright = await import("playwright")
  } catch {
    return [
      {
        test_id: "F1-UI-BROWSER",
        priority: "P0",
        title: "Chế độ Playwright Browser Chaos (F5 Slow 3G, Offline, 2 Tab)",
        status: "BLOCKED",
        root_cause: "RC-GRADER",
        detail: "Chưa cài Playwright. Chạy `npm i -D playwright && npx playwright install chromium` rồi chạy lại với --browser.",
      },
    ]
  }
  if (!opts.email || !opts.password) {
    return [
      {
        test_id: "F1-UI-BROWSER",
        priority: "P0",
        title: "Chế độ Playwright Browser Chaos",
        status: "BLOCKED",
        root_cause: "RC-GRADER",
        detail: "Cần truyền --email và --password của tài khoản test local để đăng nhập vào API Mode.",
      },
    ]
  }

  const out = []
  const shotDir = path.join(REPORT_DIR, "screenshots")
  fs.mkdirSync(shotDir, { recursive: true })
  const browser = await playwright.chromium.launch({ headless: true })
  try {
    const context = await browser.newContext()
    const page = await context.newPage()
    await page.goto(opts.url, { waitUntil: "networkidle" })

    // Attempt login if email/password form visible
    const emailInput = page.locator('input[type="email"]').first()
    if (await emailInput.isVisible({ timeout: 3000 }).catch(() => false)) {
      await emailInput.fill(opts.email)
      await page.locator('input[type="password"]').first().fill(opts.password)
      await page.locator('button[type="submit"]').first().click()
      await page.waitForLoadState("networkidle")
    }

    // Browser Check 1: F1-E13-02 paste 8,005 chars in ChatComposer
    const composer = page.locator("textarea").first()
    await composer.waitFor({ state: "visible", timeout: 8000 })
    await composer.fill("a".repeat(8005))
    const actualLen = (await composer.inputValue()).length
    const ok8k = actualLen <= 8000
    if (!ok8k) await page.screenshot({ path: path.join(shotDir, "F1-E13-02_8k_overflow.png") })
    out.push({
      test_id: "F1-E13-02-BROWSER",
      priority: "P1",
      title: "[Browser] Dán 8.005 ký tự vào ChatComposer",
      status: ok8k ? "PASS" : "BUG",
      root_cause: ok8k ? "" : "RC-FE",
      detail: ok8k ? `OK: Chặn ở ${actualLen} ký tự` : `Ô nhập nhận tới ${actualLen} ký tự (vượt ngưỡng 8.000)`,
    })

    // Browser Check 2: F1-E11-02 Slow 3G + F5 mid-Pending POST /v1/messages
    const cdp = await context.newCDPSession(page)
    await cdp.send("Network.emulateNetworkConditions", {
      offline: false,
      latency: 1800,
      downloadThroughput: 50 * 1024,
      uploadThroughput: 20 * 1024,
    })
    await composer.fill("Ngày mai 8h sáng học Toán trong 60 phút")
    await composer.press("Enter")
    await page.waitForTimeout(700)
    await page.reload({ waitUntil: "domcontentloaded" })
    await cdp.send("Network.emulateNetworkConditions", {
      offline: false,
      latency: 0,
      downloadThroughput: -1,
      uploadThroughput: -1,
    })
    await page.waitForTimeout(1500)
    await page.screenshot({ path: path.join(shotDir, "F1-E11-02_after_f5.png") })
    const hasConfirmOrCancel = await page
      .locator('button:has-text("Xác nhận"), button:has-text("Duyệt"), button:has-text("Hủy")')
      .first()
      .isVisible()
      .catch(() => false)
    out.push({
      test_id: "F1-E11-02-BROWSER",
      priority: "P0",
      title: "[Browser] Slow 3G + F5 khi request đang Pending [CF-04 / Hiển TC-08]",
      status: hasConfirmOrCancel ? "PASS" : "BUG",
      root_cause: hasConfirmOrCancel ? "" : "RC-FE",
      detail: hasConfirmOrCancel
        ? "OK: Khôi phục được nút Xác nhận/Hủy sau F5"
        : "Không thấy nút khôi phục/hủy bản nháp sau khi F5 giữa lúc Pending (xem ảnh F1-E11-02_after_f5.png)",
    })
  } finally {
    await browser.close()
  }
  return out
}

async function main() {
  const opts = parseArgs(process.argv.slice(2))
  console.log("=== StudyFlow AI – F1 Automated UI QA Runner ===")
  const results = await runLayer1Checks()
  if (opts.browser) {
    results.push(...(await runBrowserChaos(opts)))
  }

  let pass = 0
  let bug = 0
  let blocked = 0
  for (const r of results) {
    if (r.status === "PASS") pass += 1
    else if (r.status === "BLOCKED") blocked += 1
    else bug += 1
    console.log(`[${r.status.padEnd(7)}] ${r.test_id} (${r.priority}) | ${r.title}`)
    if (r.status !== "PASS") console.log(`          -> ${r.root_cause}: ${r.detail}`)
  }
  console.log("-".repeat(88))
  console.log(`TỔNG KẾT UI QA: ${pass}/${results.length} PASS | ${bug} BUG | ${blocked} BLOCKED`)

  fs.mkdirSync(REPORT_DIR, { recursive: true })
  const stamp = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19)
  const outPath = path.join(REPORT_DIR, `f1_ui_qa_report_${stamp}.json`)
  fs.writeFileSync(outPath, JSON.stringify({ generated_at: new Date().toISOString(), results }, null, 2) + "\n", "utf8")
  console.log(`Đã lưu báo cáo UI tại: ${outPath}`)
  process.exit(bug > 0 ? 1 : 0)
}

main().catch((err) => {
  console.error(err)
  process.exit(2)
})
