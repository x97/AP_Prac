import Foundation
import PDFKit
import AppKit

// Usage: swift pdf_lines.swift <input.pdf> <output.tsv> [minSize]
// Emits every text line whose maximum font size is at least minSize:
// pdf_page <TAB> line_no <TAB> max_size <TAB> all_bold <TAB> text

let args = CommandLine.arguments
guard args.count >= 3 else {
    FileHandle.standardError.write("usage: pdf_lines.swift <input.pdf> <output.tsv> [minSize]\n".data(using: .utf8)!)
    exit(2)
}
let minSize = args.count >= 4 ? (Double(args[3]) ?? 14.5) : 14.5
guard let document = PDFDocument(url: URL(fileURLWithPath: args[1])) else {
    FileHandle.standardError.write("cannot open PDF\n".data(using: .utf8)!)
    exit(1)
}

var rows: [String] = []
for pageIndex in 0..<document.pageCount {
    guard let page = document.page(at: pageIndex), let attributed = page.attributedString else { continue }
    let text = attributed.string as NSString
    var location = 0
    var lineNumber = 0
    while location < text.length {
        let lineRange = text.lineRange(for: NSRange(location: location, length: 0))
        let line = text.substring(with: lineRange).trimmingCharacters(in: .whitespacesAndNewlines)
        location = NSMaxRange(lineRange)
        lineNumber += 1
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
        if sawText && maxSize >= minSize {
            let cleaned = line.replacingOccurrences(of: "\t", with: " ")
            rows.append("\(pageIndex + 1)\t\(lineNumber)\t\(String(format: "%.1f", maxSize))\t\(allBold ? "B" : "-")\t\(cleaned)")
        }
    }
}
try rows.joined(separator: "\n").write(to: URL(fileURLWithPath: args[2]), atomically: true, encoding: .utf8)
FileHandle.standardError.write("wrote \(rows.count) lines to \(args[2])\n".data(using: .utf8)!)
