from crc.api.file import get_document_directory


def render_files(study_id,irb_codes):
    files = get_document_directory(study_id)
    print(files)