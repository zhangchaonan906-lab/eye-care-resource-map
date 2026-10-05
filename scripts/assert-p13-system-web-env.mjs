const required = [
  "APP_ENV",
  "P13_SYSTEM_TEST_MODE",
  "TRUST_PROXY_HEADERS",
  "RATE_LIMIT_HASH_SECRET",
  "UPSTASH_REDIS_REST_URL",
  "UPSTASH_REDIS_REST_TOKEN",
];
const missing = required.filter((name) => !process.env[name]);
if (missing.length > 0) {
  throw new Error(`P13 system web server is missing required test environment variables: ${missing.join(", ")}`);
}
if (process.env.APP_ENV !== "staging" || process.env.P13_SYSTEM_TEST_MODE !== "true") {
  throw new Error("P13 system web server must use the isolated staging test mode");
}
process.stdout.write("P13 system web-server rate-limit environment is configured.\n");
