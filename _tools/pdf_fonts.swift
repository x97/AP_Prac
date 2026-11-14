import Foundation
import PDFKit
import AppKit

// Usage: swift pdf_fonts.swift <input.pdf> <page> [<page> ...]
// Prints each text line with the set of font sizes/names seen in it.

let args = CommandLine.arguments
guard args.count >= 3 else {
    FileHandle.standardError.write("usage: pdf_fonts.swift <input.pdf> <page> [...]\n".data(using: .utf8)!)
    exit(2)
}
guard let document = PDFDocument(url: URL(fileURLWithPath: args[1])) else {
    FileHandle.standardError.write("cannot open PDF\n".data(using: .utf8)!)
    exit(1)
}

for arg in args.dropFirst(2) {
    guard let pageNumber = Int(arg), pageNumber >= 1, pageNumber <= document.pageCount,
          let page = document.page(at: pageNumber - 1),
          let attributed = page.attributedString else {
        print("=== PAGE \(arg) (no attributed string) ===")
        continue
    }
    print("=== PAGE \(pageNumber) ===")
    let text = attributed.string as NSString
    var lineStart = 0
    var lineNumber = 1
    while lineStart < text.length {
        let lineRange = text.lineRange(for: NSRange(location: lineStart, length: 0))
        let trimmedRange = (text.substring(with: lineRange) as NSString)
        var display = text.substring(with: lineRange).trimmingCharacters(in: .whitespacesAndNewlines)
        if !display.isEmpty {
            var specs: [String] = []
            attributed.enumerateAttributes(in: lineRange, options: []) { attrs, range, _ in
                let font = attrs[.font] as? NSFont
                let size = font?.pointSize ?? 0
                let name = font?.fontName ?? "?"
                let bold = (font?.fontDescriptor.symbolicTraits.contains(.bold) ?? false)
                let spec = String(format: "%.1f:%@%@", size, name, bold ? ":B" : "")
                if !specs.contains(spec) { specs.append(spec) }
            }
            print(String(format: "%4d | %@ | %@", lineNumber, specs.joined(separator: ","), display))
        }
        lineStart = NSMaxRange(lineRange)
        lineNumber += 1
    }
}
