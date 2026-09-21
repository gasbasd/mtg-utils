import xlrd


def read_list(file_path):
    with open(file_path, "r") as file:
        return [line.strip() for line in file if line.strip()]


def read_xls_rows(file_path: str, sheet_index: int = 0) -> list[dict[str, str | float | bool]]:
    """Read a sheet from a legacy .xls workbook as a list of {header: cell value} dicts.

    Row 0 supplies the headers. Cell values are returned exactly as xlrd produces them
    (text, float, bool) so that coercion stays in the caller's pure logic.
    """
    sheet = xlrd.open_workbook(file_path).sheet_by_index(sheet_index)
    if not sheet.nrows:
        return []
    headers = [str(cell.value).strip() for cell in sheet.row(0)]
    return [dict(zip(headers, (cell.value for cell in sheet.row(index)))) for index in range(1, sheet.nrows)]
