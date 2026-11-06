const { version } = require("../package.json");

function checkReleaseVersion({ version, eventName, tag }) {
  if (!/^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$/.test(version)) {
    throw new Error("The desktop package version must be a semantic version.");
  }
  if (eventName === "release" && tag !== `v${version}`) {
    throw new Error(`Release tag must exactly match v${version}.`);
  }
  return version;
}

if (require.main === module) {
  try {
    console.log(checkReleaseVersion({
      version,
      eventName: process.env.GITHUB_EVENT_NAME,
      tag: process.env.RELEASE_TAG,
    }));
  } catch (error) {
    console.error(error.message);
    process.exitCode = 1;
  }
}

module.exports = { checkReleaseVersion };
