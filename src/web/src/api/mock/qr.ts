/**
 * Draws a QR-like SVG for the mock label. It is NOT scannable; the real API returns a
 * genuine QR code in ReturnLabelResponse.qr_svg.
 */
export function mockQrSvg(text: string): string {
  const size = 25
  let seed = [...text].reduce((h, c) => (h * 31 + c.charCodeAt(0)) >>> 0, 7)
  const next = () => {
    seed = (seed * 1103515245 + 12345) >>> 0
    return seed / 2 ** 32
  }
  const inFinder = (x: number, y: number) =>
    (x < 8 && y < 8) || (x >= size - 8 && y < 8) || (x < 8 && y >= size - 8)
  const finder = (ox: number, oy: number) =>
    `<rect x="${ox}" y="${oy}" width="7" height="7" fill="#000"/>` +
    `<rect x="${ox + 1}" y="${oy + 1}" width="5" height="5" fill="#fff"/>` +
    `<rect x="${ox + 2}" y="${oy + 2}" width="3" height="3" fill="#000"/>`

  let cells = ''
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      if (!inFinder(x, y) && next() > 0.5) cells += `<rect x="${x}" y="${y}" width="1" height="1"/>`
    }
  }
  return (
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="-2 -2 ${size + 4} ${size + 4}" shape-rendering="crispEdges">` +
    `<rect x="-2" y="-2" width="${size + 4}" height="${size + 4}" fill="#fff"/>` +
    `<g fill="#000">${cells}</g>${finder(0, 0)}${finder(size - 7, 0)}${finder(0, size - 7)}</svg>`
  )
}
