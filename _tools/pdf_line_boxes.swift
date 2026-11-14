import Foundation
import PDFKit

// Usage: swift pdf_line_boxes.swift <input.pdf> <output.tsv> [firstPage] [lastPage]
// Emits: page \t line_no \t x \t y \t w \t h \t text
// Uses PDFSelection.selectionsByLine(), which keeps visually separate lines apart.

let args = CommandLine.arguments
guard args.count >= 3 else {
    FileHandle.standardError.write("usage: pdf_line_boxes.swift <input.pdf> <output.tsv> [first] [last]\n".data(using: .utf8)!)
    exit(2)
}
guard let document = PDFDocument(url: URL(fileURLWithPath: args[1])) else {
    FileHandle.standardError.write("cannot open PDF\n".data(using: .utf8)!)
    exit(1)
}
let total = document.pageCount
let first = args.count >= 4 ? max(1, Int(args[3]) ?? 1) : 1
let last = args.count >= 5 ? min(total, Int(args[4]) ?? total) : total

var rows: [String] = []
for index in (first - 1)..<last {
    guard let page = document.page(at: index), let attributed = page.attributedString else { continue }
    let fullRange = NSRange(location: 0, length: attributed.length)
    guard let full = page.selection(for: fullRange) else { continue }
    let lines = full.selectionsByLine()
    var lineNo = 0
    for line in lines {
        let text = (line.string ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
        if text.isEmpty { continue }
        lineNo += 1
        let b = line.bounds(for: page)
        let cleaned = text.replacingOccurrences(of: "\t", with: " ")
        rows.append(String(format: "%d\t%d\t%.2f\t%.2f\t%.2f\t%.2f\t%@",
                           index + 1, lineNo, b.origin.x, b.origin.y, b.width, b.height, cleaned))
    }
}
try rows.joined(separator: "\n").write(to: URL(fileURLWithPath: args[2]), atomically: true, encoding: .utf8)
FileHandle.standardError.write("wrote \(rows.count) lines\n".data(using: .utf8)!)
