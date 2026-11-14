import Foundation
import PDFKit

// Usage: swift pdf_text.swift <input.pdf> <output.txt> [firstPage] [lastPage]
// Emits one block per page:
// === PAGE <n> ===
// <page text>

let args = CommandLine.arguments
guard args.count >= 3 else {
    FileHandle.standardError.write("usage: pdf_text.swift <input.pdf> <output.txt> [first] [last]\n".data(using: .utf8)!)
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

var out = ""
for index in (first - 1)..<last {
    guard let page = document.page(at: index) else { continue }
    out += "=== PAGE \(index + 1) ===\n"
    out += (page.string ?? "") + "\n"
}
try out.write(to: outputURL, atomically: true, encoding: .utf8)
FileHandle.standardError.write("pages \(first)-\(last) of \(total) -> \(outputURL.path)\n".data(using: .utf8)!)
