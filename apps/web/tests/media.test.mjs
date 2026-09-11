import assert from "node:assert/strict";
import test from "node:test";
import { selectResultMedia } from "../lib/media.ts";

const result = {
  media_verified_at: "2026-09-12T00:00:00Z",
  institution_logo_url: "https://official.example/logo.png",
  campus_image_url: null,
  provider_logo_url: "https://provider.example/logo.png",
  scheme_logo_url: null,
};

test("verified institution logo is selected", () => {
  assert.deepEqual(selectResultMedia(result, false), {
    url: "https://official.example/logo.png",
    kind: "logo",
  });
});

test("verified campus image takes priority over an institution logo", () => {
  assert.deepEqual(
    selectResultMedia({ ...result, campus_image_url: "https://official.example/campus.jpg" }, false),
    { url: "https://official.example/campus.jpg", kind: "campus" },
  );
});

test("verified scholarship provider logo is selected", () => {
  assert.deepEqual(selectResultMedia(result, true), {
    url: "https://provider.example/logo.png",
    kind: "logo",
  });
});

test("missing, unverified, or unsafe media uses the fallback path", () => {
  assert.equal(selectResultMedia({ ...result, media_verified_at: null }, false), null);
  assert.equal(
    selectResultMedia({ ...result, institution_logo_url: "javascript:alert(1)" }, false),
    null,
  );
  assert.equal(selectResultMedia({ ...result, institution_logo_url: null }, false), null);
});
