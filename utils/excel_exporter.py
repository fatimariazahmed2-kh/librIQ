import os
import csv
import datetime
from tkinter import filedialog

try:
    import pandas as pd
except ImportError:
    pd = None

try:
    import openpyxl  # noqa: F401  (import check only)
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False

# All export failures are logged here so problems are never silent,
# even when the calling code does not check the returned result.
_LOG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "backup_errors.log")


def _log_error(context: str, error: str):
    try:
        os.makedirs(os.path.dirname(_LOG_PATH), exist_ok=True)
        with open(_LOG_PATH, "a", encoding="utf-8") as f:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] {context}: {error}\n")
    except Exception:
        # Logging itself must never crash the app.
        pass


class ExcelExporter:
  """Utility engine to export database records into neatly formatted Excel files."""

  @staticmethod
  def export_table_to_excel(
      columns: list, rows: list, default_filename: str = "export.xlsx", file_path: str = None
  ):
    """Writes rows to an Excel workbook, using file_path when provided or showing save dialog otherwise.

    Returns a dict: {"success": bool, "message": str}.
    "success" is only True when the actual .xlsx file was written. Any fallback
    or failure is reported clearly instead of being disguised as success.
    """
    try:
      if not file_path:
        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel Files", "*.xlsx"), ("All Files", "*.*")],
            initialfile=default_filename,
            title="Export Data to Excel",
        )

        if not file_path:
          return {"success": False, "message": "Export cancelled by user."}

      # ---- Missing dependency checks (reported clearly, not hidden) ----
      if pd is None:
        msg = "'pandas' library is not installed. Run: pip install pandas openpyxl"
        _log_error(f"Export to {file_path}", msg)
        return ExcelExporter._csv_fallback(columns, rows, file_path, msg)

      if not HAS_OPENPYXL:
        msg = "'openpyxl' library is not installed. Run: pip install openpyxl"
        _log_error(f"Export to {file_path}", msg)
        return ExcelExporter._csv_fallback(columns, rows, file_path, msg)

      # ---- Actual Excel write ----
      try:
        df = pd.DataFrame(rows, columns=columns)
        with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
          df.to_excel(writer, index=False, sheet_name="Exported_Data")

        return {
            "success": True,
            "message": f"Data successfully exported to '{os.path.basename(file_path)}'!",
        }

      except PermissionError:
        # Most common real-world cause: the .xlsx file is currently open in Excel.
        msg = (
            f"Could not write '{os.path.basename(file_path)}' because the file "
            "is currently open (likely in Excel). Please close it and try again."
        )
        _log_error(f"Export to {file_path}", msg)
        return {"success": False, "message": msg}

      except Exception as e:
        msg = f"Excel write failed: {str(e)}"
        _log_error(f"Export to {file_path}", msg)
        return ExcelExporter._csv_fallback(columns, rows, file_path, msg)

    except Exception as e:
      msg = f"Excel Export Failed: {str(e)}"
      _log_error(f"Export to {file_path}", msg)
      return {"success": False, "message": msg}

  @staticmethod
  def _csv_fallback(columns: list, rows: list, file_path: str, reason: str):
    """Writes a CSV copy so data is not lost, but always reports success=False
    for the .xlsx request so the caller/UI can surface the real problem."""
    try:
      csv_path = file_path
      if csv_path.lower().endswith(".xlsx"):
        csv_path = csv_path[:-5] + ".csv"
      with open(csv_path, mode="w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(columns)
        writer.writerows(rows)
      return {
          "success": False,
          "message": f"{reason} (Data was saved as CSV backup: '{os.path.basename(csv_path)}')",
      }
    except Exception as e:
      _log_error(f"CSV fallback for {file_path}", str(e))
      return {"success": False, "message": f"{reason} (CSV fallback also failed: {str(e)})"}