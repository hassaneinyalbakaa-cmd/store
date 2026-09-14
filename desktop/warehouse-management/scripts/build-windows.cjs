const { spawnSync } = require("node:child_process");
const path = require("node:path");

const target = process.argv[2];
if (!["portable", "nsis"].includes(target)) {
  console.error("Usage: node scripts/build-windows.cjs <portable|nsis>");
  process.exit(2);
}

const hasCertificateFile = Boolean(process.env.WIN_CSC_LINK || process.env.CSC_LINK);
const certificateSubjectName = process.env.WINDOWS_CERTIFICATE_SUBJECT_NAME;

if (!hasCertificateFile && !certificateSubjectName) {
  console.error(
    [
      "Windows code-signing credentials are required.",
      "Set WIN_CSC_LINK and WIN_CSC_KEY_PASSWORD for a PFX/P12 certificate,",
      "or set WINDOWS_CERTIFICATE_SUBJECT_NAME on a Windows build host.",
      "The build was stopped to prevent distributing an unsigned executable.",
    ].join("\n"),
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