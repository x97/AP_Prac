import Foundation
import PDFKit
import AppKit

// Usage: swift pdf_layout.swift <input.pdf> <output.tsv> [firstPage] [lastPage]
// Emits: page \t line_no \t x \t y \t w \t h \t max_size \t all_bold \t text

let args = CommandLine.arguments
guard args.count >= 3 else {
    FileHandle.standardError.write("usage: pdf_layout.swift <input.pdf> <output.tsv> [first] [last]\n".data(using: .utf8)!)
    exit(2)
}
let inputURL = URL(fileURLWithPath: args[1])
let outputURL = URL(fileURLWithPath: args[2])
guard let document = PDFDocument(url: inputURL) else {
    FileHandle.standardError.write("cannot open PDF\n".data(using: .utf8)!)
    exit(1)
}
let total = document.pageCount
let first = args.count >= 4 ? max(1, Int(args[3]) ?? 1) : 1
let last = args.count >= 5 ? min(total, Int(args[4]) ?? total) : total

var rows: [String] = []
for index in (first - 1)..<last {
    guard let page = document.page(at: index), let attributed = page.attributedString else { continue }
    let text = attributed.string as NSString
    var location = 0
    var lineNo = 0
    while location < text.length {
        let lineRange = text.lineRange(for: NSRange(location: location, length: 0))
        let raw = text.substring(with: lineRange)
        let line = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        location = NSMaxRange(lineRange)
        lineNo += 1
        if line.isEmpty { continue }

        var allBold = true
        var maxSize = 0.0
        var sawText = false
        attributed.enumerateAttributes(in: lineRange, options: []) { attrs, range, _ in
            let piece = (text.substring(with: range) as NSString).trimmingCharacters(in: .whitespacesAndNewlines)
            guard !piece.isEmpty else { return }
            sawText = true
            let font = attrs[.font] as? NSFont
            let size = font?.pointSize ?? 0
            let bold = font?.fontDescriptor.symbolicTraits.contains(.bold) ?? false
            if size > maxSize { maxSize = size }
            if !bold { allBold = false }
        }
        guard sawText else { continue }

        let bounds = page.selection(for: lineRange)?.bounds(for: page) ?? .zero
        let cleaned = line.replacingOccurrences(of: "\t", with: " ")
        rows.append(String(format: "%d\t%d\t%.2f\t%.2f\t%.2f\t%.2f\t%.1f\t%@\t%@",
                           index + 1, lineNo, bounds.origin.x, bounds.origin.y,
                           bounds.width, bounds.height, maxSize, allBold ? "B" : "-", cleaned))
    }
}
try rows.joined(separator: "\n").write(to: outputURL, atomically: true, encoding: .utf8)
FileHandle.standardError.write("wrote \(rows.count) lines to \(outputURL.path)\n".data(using: .utf8)!)
