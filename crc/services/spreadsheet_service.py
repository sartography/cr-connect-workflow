from openpyxl import Workbook
from tempfile import NamedTemporaryFile


class SpreadsheetService(object):

    @staticmethod
    def create_spreadsheet(data: list[dict], headers: list[str] = None, title: str = None):
        """The length of headers must be the same as the number of items in the dictionaries,
           and the order must match up.
           The title is used for the worksheet, not the filename."""

        wb = Workbook(write_only=True)
        ws = wb.create_sheet()
        if title:
            ws.title = title
        if headers:
            ws.append(headers)
        for row in data:
            ws.append(list(row.values()))

        with NamedTemporaryFile() as tmp:
            wb.save(tmp.name)
            tmp.seek(0)
            stream = tmp.read()
            return stream
