// Minimal macOS Vision OCR helper used by _tools/parse_ap_psych_2016_2017.py.
//
// Usage:
//   swiftc _tools/vision_ocr.swift -o /tmp/ap_psych_vision_ocr
//   /tmp/ap_psych_vision_ocr page.png > page.json
//
// Output is a JSON array of observations with normalized coordinates. The
// origin is bottom-left, matching Vision's VNRecognizedTextObservation.
import Foundation
import Vision
import AppKit

let args = CommandLine.arguments
guard args.count >= 2 else {
    FileHandle.standardError.write(Data("usage: vision_ocr <image>\n".utf8))
    exit(2)
}
let url = URL(fileURLWithPath: args[1])
guard let image = NSImage(contentsOf: url),
      let tiff = image.tiffRepresentation,
      let rep = NSBitmapImageRep(data: tiff),
      let cg = rep.cgImage else {
    FileHandle.standardError.write(Data("cannot read image: \(url.path)\n".utf8))
    exit(1)
}
let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.usesLanguageCorrection = true
request.recognitionLanguages = ["en-US"]
let handler = VNImageRequestHandler(cgImage: cg, options: [:])
do {
    try handler.perform([request])
} catch {
    FileHandle.standardError.write(Data("Vision OCR failed: \(error)\n".utf8))
    exit(1)
}
var rows: [[String: Any]] = []
for obs in (request.results ?? []) {
    guard let candidate = obs.topCandidates(1).first else { continue }
    let b = obs.boundingBox
    rows.append([
        "text": candidate.string,
        "confidence": candidate.confidence,
        "x": b.origin.x,
        "y": b.origin.y,
        "w": b.size.width,
        "h": b.size.height,
    ])
}
let data = try JSONSerialization.data(withJSONObject: rows, options: [.prettyPrinted, .sortedKeys])
print(String(data: data, encoding: .utf8)!)
