const PNG = new Set(["CN035", "CN038", "CN039"]);

export function productPhoto(sku: string) {
  const code = sku || "";
  const ext = PNG.has(code) ? "png" : "jpg";
  return `/products/${code}.${ext}`;
}
