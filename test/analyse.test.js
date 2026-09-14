import { test } from "node:test";
import assert from "node:assert/strict";
import { buildContent } from "../src/analyse.js";

test("buildContent maps files to the right block types", () => {
  const files = [
    { originalname: "sheet.pdf", mimetype: "application/pdf", buffer: Buffer.from("%PDF-1.4") },
    { originalname: "photo.jpg", mimetype: "image/jpeg", buffer: Buffer.from([1, 2, 3]) },
    { originalname: "comps.csv", mimetype: "text/csv", buffer: Buffer.from("a,b\n1,2") },
    { originalname: "deal.docx", mimetype: "application/vnd.openxmlformats-officedocument.wordprocessingml.document", buffer: Buffer.from("x") },
  ];
  const { content, unsupported } = buildContent({ notes: "hello", files, submitter: { name: "Sam" } });
  assert.deepEqual(content.map((c) => c.type), ["document", "image", "text", "text"]);
  assert.equal(content[0].source.media_type, "application/pdf");
  assert.equal(content[0].title, "sheet.pdf");
  assert.match(content[2].text, /comps\.csv/);
  assert.match(content[3].text, /Sent in by: Sam/);
  assert.match(content[3].text, /hello/);
  assert.deepEqual(unsupported, ["deal.docx"]);
});
