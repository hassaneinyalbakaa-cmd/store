const { test } = require("node:test");
const assert = require("node:assert/strict");
const { checkReleaseVersion } = require("./check-release-version.cjs");

test("accepts only the matching release tag", () => {
  assert.equal(checkReleaseVersion({
    version: "1.0.0", eventName: "release", tag: "v1.0.0",
  }), "1.0.0");
  for (const tag of ["v2.0.0", "1.0.0", "", undefined]) {
    assert.throws(() => checkReleaseVersion({
      version: "1.0.0", eventName: "release", tag,
    }));
  }
});

test("manual builds do not require publishing a release", () => {
  assert.equal(checkReleaseVersion({
    version: "1.0.0", eventName: "workflow_dispatch",
  }), "1.0.0");
});

test("allows prereleases and rejects malformed package versions", () => {
  assert.equal(checkReleaseVersion({
    version: "1.0.1-rc.1", eventName: "release", tag: "v1.0.1-rc.1",
  }), "1.0.1-rc.1");
  assert.throws(() => checkReleaseVersion({
    version: "version1", eventName: "workflow_dispatch",
  }));
});
