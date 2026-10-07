// OCR of every .jpg and .png in a folder with Apple Vision (accurate mode), one JSON line per frame.
// macOS only. Do not run it directly: ocr.sh compiles it once into a cache folder and runs it.
//
//   ocr <frames_dir> <out.jsonl> [lang,lang]      default languages: en-US
//
// Output line: {"f": "00042.jpg", "lines": [{"t": "text", "x": 0.12, "y": 0.34, "w": 0.2, "h": 0.02, "c": 0.98}]}
// Boxes are normalized (0 to 1) with y measured from the top; c is the recognition confidence.
// Feed the result to ocr_events.py to get a timeline of stable on-screen text.
import AppKit
import Foundation
import Vision

let args = CommandLine.arguments
guard args.count >= 3 else {
    FileHandle.standardError.write("usage: ocr <frames_dir> <out.jsonl> [lang,lang]\n".data(using: .utf8)!)
    exit(2)
}
let dir = args[1], out = args[2]
let langs = args.count > 3 ? args[3].split(separator: ",").map(String.init) : ["en-US"]
let fm = FileManager.default
let files = try fm.contentsOfDirectory(atPath: dir)
    .filter { $0.lowercased().hasSuffix(".jpg") || $0.lowercased().hasSuffix(".png") }
    .sorted()
fm.createFile(atPath: out, contents: nil)
guard let handle = FileHandle(forWritingAtPath: out) else {
    FileHandle.standardError.write("cannot write \(out)\n".data(using: .utf8)!)
    exit(1)
}
var done = 0
for f in files {
    let url = URL(fileURLWithPath: dir).appendingPathComponent(f)
    guard let img = NSImage(contentsOf: url),
          let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else { continue }
    let req = VNRecognizeTextRequest()
    req.recognitionLevel = .accurate
    req.usesLanguageCorrection = false
    req.recognitionLanguages = langs
    try? VNImageRequestHandler(cgImage: cg, options: [:]).perform([req])
    var lines: [[String: Any]] = []
    for o in req.results ?? [] {
        guard let c = o.topCandidates(1).first else { continue }
        let b = o.boundingBox
        lines.append([
            "t": c.string,
            "x": (b.minX * 1000).rounded() / 1000, "y": ((1 - b.maxY) * 1000).rounded() / 1000,
            "w": (b.width * 1000).rounded() / 1000, "h": (b.height * 1000).rounded() / 1000,
            "c": (Double(c.confidence) * 100).rounded() / 100,
        ])
    }
    let data = try JSONSerialization.data(withJSONObject: ["f": f, "lines": lines])
    handle.write(data)
    handle.write("\n".data(using: .utf8)!)
    done += 1
}
print("\(done) frames -> \(out)")
