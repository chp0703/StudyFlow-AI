"""Private worker: no filenames, provider secrets or parser warnings reach logs."""

import io
import json
import sys


def main():
    try:
        max_bytes, max_pages, max_text = (map(int, sys.argv[1:]) if len(sys.argv) > 1
                                          else (5 * 1024 * 1024, 20, 24000))
        from pypdf import PdfReader, overwrite_configuration
    except ImportError:
        print(json.dumps({'error': 'DEPENDENCY_MISSING'}))
        return 1
    try:
        overwrite_configuration(
            maximum_declared_stream_length=1024 * 1024,
            zlib_maximum_output_length=1024 * 1024,
            lzw_maximum_output_length=1024 * 1024,
            run_length_maximum_output_length=1024 * 1024,
            array_based_stream_maximum_output_length=1024 * 1024,
            stream_decoding_work_maximum_length=5 * 1024 * 1024,
        )
        content = sys.stdin.buffer.read(max_bytes + 1)
        if len(content) > max_bytes:
            raise ValueError()
        reader = PdfReader(io.BytesIO(content), strict=True,
                           xref_stream_maximum_entries=100000)
        if reader.is_encrypted or not 1 <= len(reader.pages) <= max_pages:
            raise ValueError()
        pieces = []
        char_count = 0
        for page in reader.pages:
            stream = page.get_contents()
            if stream is not None and len(stream.get_data()) > 1024 * 1024:
                raise ValueError()
            text = page.extract_text()
            if not text or not text.strip():
                raise ValueError()
            pieces.append(text)
            char_count += len(text) + (1 if len(pieces) > 1 else 0)
            if char_count > max_text:
                raise ValueError()
        print(json.dumps({'pages': pieces}))
        return 0
    except Exception:
        print(json.dumps({'error': 'INVALID_PDF'}))
        return 1


if __name__ == '__main__':
    sys.exit(main())
