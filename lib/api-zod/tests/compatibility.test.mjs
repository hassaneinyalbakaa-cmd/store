import { test } from "node:test";
import assert from "node:assert/strict";
import {
  LoginBody,
  GetCurrentUserResponse,
  CreateReceiptBody,
  CreateIssueRequestBody,
  GetReportResponse,
} from "../src/generated/api.ts";

test("login input and session permissions retain their contracts", () => {
  assert.equal(LoginBody.safeParse({ username: "", password: "" }).success, false);
  assert.equal(LoginBody.safeParse({ username: "operator", password: "example" }).success, true);
  const session = {
    id: 1, username: "operator", display_name: "مشغل",
    role_id: 1, role_name: "admin", permissions: ["inventory:read"], is_active: true,
  };
  assert.deepEqual(GetCurrentUserResponse.parse(session), session);
  assert.equal(GetCurrentUserResponse.safeParse({ ...session, permissions: [1] }).success, false);
});

test("receipt lines retain date coercion and positive quantity validation", () => {
  const detail = { item_id: 1, warehouse_id: 1, quantity: 5 };
  const receipt = { receipt_date: "2026-11-06", supplier: "مورد اختبار", details: [detail] };
  assert.ok(CreateReceiptBody.parse(receipt).receipt_date instanceof Date);
  assert.equal(CreateReceiptBody.safeParse({ ...receipt, details: [] }).success, false);
  for (const quantity of [0, -1, NaN, Infinity, "5"]) {
    assert.equal(CreateReceiptBody.safeParse({
      ...receipt, details: [{ ...detail, quantity }],
    }).success, false);
  }
});

test("issue requests reject missing reasons and nonpositive quantities", () => {
  const request = {
    department_id: 1, request_date: "2026-11-06",
    reason: "اختبار", item_id: 1, quantity: 2,
  };
  assert.ok(CreateIssueRequestBody.parse(request).request_date instanceof Date);
  assert.equal(CreateIssueRequestBody.safeParse({ ...request, reason: "" }).success, false);
  assert.equal(CreateIssueRequestBody.safeParse({ ...request, quantity: 0 }).success, false);
});

test("report records accept dynamic columns and coerce timestamps", () => {
  const report = {
    report_type: "inventory-balance", title: "المخزون",
    columns: [{ key: "quantity", label: "الكمية" }],
    rows: [{ quantity: 5, warehouse: "المخزن الرئيسي", expiry_date: null }],
    generated_at: "2026-11-06T12:00:00Z", row_count: 1,
  };
  const parsed = GetReportResponse.parse(report);
  assert.deepEqual(parsed.rows, report.rows);
  assert.ok(parsed.generated_at instanceof Date);
  assert.equal(GetReportResponse.safeParse({ ...report, report_type: "unknown" }).success, false);
});
