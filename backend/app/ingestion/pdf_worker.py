"""Private worker: no filenames, provider secrets or parser warnings reach logs."""

import io
import json
import sys


def main():
    try:
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
        reader = PdfReader(io.BytesIO(sys.stdin.buffer.read(5 * 1024 * 1024 + 1)), strict=True,
                           xref_stream_maximum_entries=100000)
        if reader.is_encrypted or not 1 <= len(reader.pages) <= 20:
            raise ValueError()
        pieces = []
        for page in reader.pages:
            stream = page.get_contents()
            if stream is not None and len(stream.get_data()) > 1024 * 1024:
                raise ValueError()
            text = page.extract_text()
            if not text or not text.strip():
                raise ValueError()
            pieces.append(text)
            if sum(len(p) + 1 for p in pieces) > 24000:
                raise ValueError()
        print(json.dumps({'text': '\n'.join(pieces)}))
        return 0
    except Exception:
        print(json.dumps({'error': 'INVALID_PDF'}))
        return 1


if __name__ == '__main__':
    sys.exit(main())
