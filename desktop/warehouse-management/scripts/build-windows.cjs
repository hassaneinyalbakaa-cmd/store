const { spawnSync } = require("node:child_process");
const path = require("node:path");

const target = process.argv[2];
if (!["portable", "nsis"].includes(target)) {
  console.error(
    "Usage: node scripts/build-windows.cjs <portable|nsis> [--require-signing]",
  );
  process.exit(2);
}

const requireSigning = process.argv.includes("--require-signing");
const certificateLink = process.env.WIN_CSC_LINK;
const certificateSubjectName = process.env.WINDOWS_CERTIFICATE_SUBJECT_NAME;
const hasSigningIdentity = Boolean(certificateLink || certificateSubjectName);

if (requireSigning && !hasSigningIdentity) {
  console.error(
    "A signing identity is required. Set WIN_CSC_LINK (PFX/P12) and " +
      "WIN_CSC_KEY_PASSWORD, or set WINDOWS_CERTIFICATE_SUBJECT_NAME on Windows.",
  );
  process.exit(1);
}

if (requireSigning && certificateLink && !process.env.WIN_CSC_KEY_PASSWORD) {
  console.error(
    "WIN_CSC_KEY_PASSWORD is required when WIN_CSC_LINK points to a PFX/P12 certificate.",
  );
  process.exit(1);
}

const builder = path.join(
  __dirname,
  "..",
  "node_modules",
  ".bin",
  process.platform === "win32" ? "electron-builder.cmd" : "electron-builder",
);
const args = ["--win", target, "--x64"];

if (requireSigning) {
  args.push("--config.forceCodeSigning=true");
}

if (certificateSubjectName) {
  args.push(
    `--config.win.signtoolOptions.certificateSubjectName=${certificateSubjectName}`,
  );
}

const result = spawnSync(builder, args, {
  cwd: path.join(__dirname, ".."),
  env: process.env,
  stdio: "inherit",
});

if (result.error) {
  console.error(result.error.message);
  process.exit(1);
}
process.exit(result.status ?? 1);