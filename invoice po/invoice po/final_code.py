import os
import zipfile
import subprocess
import re
from datetime import datetime
from doctr.io import DocumentFile
from doctr.models import ocr_predictor
import cx_Oracle
import pandas as pd
from difflib import SequenceMatcher
print("✅ Loading OCR model (one time)...")
OCR_MODEL = ocr_predictor(pretrained=True)
print("✅ OCR model loaded")

ALL_COMPARISONS = []

BASE_DIR = "invoices_12th_may"
os.makedirs(BASE_DIR, exist_ok=True)
SUPPORTED_OCR_EXT = {"pdf", "jpg", "jpeg", "png"}
ZIP_EXT = {"zip"}

# OCR
def extract_text_from_invoice(file_path):
    print("🔍 OCR started:", file_path)

    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        doc = DocumentFile.from_pdf(file_path)
    else:
        doc = DocumentFile.from_images(file_path)

    result = OCR_MODEL(doc)   # ✅ use global model

    text = ""
    for page in result.pages:
        for block in page.blocks:
            for line in block.lines:
                text += " ".join(w.value for w in line.words) + "\n"

    print("✅ OCR completed, text length:", len(text))

    with open(file_path + "_text.txt", "w", encoding="utf-8") as f:
        f.write(text)

    return text

# ZIP HANDLING

def handle_zip(file_path):
    unzip_dir = file_path + "_unzipped"
    os.makedirs(unzip_dir, exist_ok=True)
    extracted = []

    with zipfile.ZipFile(file_path, "r") as z:
        z.extractall(unzip_dir)

    for root, _, files in os.walk(unzip_dir):
        for f in files:
            if f.split(".")[-1].lower() in SUPPORTED_OCR_EXT:
                extracted.append(os.path.join(root, f))

    return extracted

def convert_docx_xlsx_to_pdf(input_file):
    out_dir = os.path.join(BASE_DIR, "converted_pdfs")
    os.makedirs(out_dir, exist_ok=True)

    subprocess.run(
        ["soffice", "--headless", "--convert-to", "pdf", input_file, "--outdir", out_dir],
        check=True
    )

    return os.path.join(out_dir, os.path.splitext(os.path.basename(input_file))[0] + ".pdf")


def extract_po_from_invoice_text(ocr_text, db_po):
    digits = re.findall(r"\d{6}", db_po or "")
    if not digits:
        return None

    six_digit = digits[0]
    return db_po if six_digit in ocr_text else None

def save_blob_file(blob_bytes, file_name, ext, output_dir):
  base_name = os.path.splitext(file_name)[0]

  file_path = os.path.join(output_dir, f"{base_name}.{ext}")

  counter = 1
  while os.path.exists(file_path):
    file_path = os.path.join(output_dir, f"{base_name}_{counter}.{ext}")
    counter += 1

  if blob_bytes:
    with open(file_path, "wb") as f:
     f.write(blob_bytes)

  return file_path


# STATE LOGIC (ONLY YOUR RULES)
def extract_state_from_place_of_supply(lines):
    for line in lines:
        if "place of supply" in line.lower():
            cleaned = line.replace(":", " ").replace("-", " ")
            for token in cleaned.split():
                if token.isdigit() and len(token) == 2:
                    return token
    return None


def extract_state_from_invoice(text, po_state):
    text_upper = text.upper()
    lines = text.splitlines()

    if po_state and po_state.upper() in text_upper:
        return po_state

    return extract_state_from_place_of_supply(lines)


# DATE EXTRACTION

def extract_invoice_date(lines, db_po_date):
    db_date_only = db_po_date.date() if db_po_date else None
    keywords = ("invoice date", "invoice", "date")

    for i, line in enumerate(lines):
        token = line.replace(":", "").strip()

        for fmt in ("%d-%b-%Y","%d.%b.%Y","%d %b %Y","%d-%B-%Y","%d.%B.%Y","%d %B %Y","%d.%m.%Y","%d-%m-%Y","%d/%m/%Y"):
            try:
                parsed_date = datetime.strptime(token, fmt).date()
            except:
                continue

            # ✅ Skip PO date
            if db_date_only and parsed_date == db_date_only:
                continue

            # ✅ Check previous line for keyword
            prev_line = lines[i-1].lower() if i > 0 else ""
            if any(k in prev_line for k in keywords):
                return parsed_date

    return None



def extract_po_date_from_pdf_matching_db(lines, db_po_date):
    if not db_po_date:
        return None

    db_date_only = db_po_date.date()

    for line in lines:
        token = line.replace(":", "").strip()

        for fmt in ("%d-%b-%Y","%d.%b.%Y","%d %b %Y","%d-%B-%Y","%d.%B.%Y","%d %B %Y","%d.%m.%Y","%d-%m-%Y","%d/%m/%Y"):
            try:
                pdf_date = datetime.strptime(token, fmt).date()
                if pdf_date == db_date_only:
                    return pdf_date
            except:
                pass

    return None



#it is used to normalize clean vendor name
def normalize_text(text):
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"[^a-z0-9 ]", " ", text)   # remove symbols
    text = re.sub(r"\s+", " ", text).strip() # remove extra spaces
    return text


def vendor_match(db_vendor, ocr_text, threshold=0.70):
    if not db_vendor or not ocr_text:
        return False

    db_vendor = normalize_text(db_vendor)

    # ✅ compare vendor against EACH OCR line
    for line in ocr_text.splitlines():
        line_norm = normalize_text(line)

        # skip very small lines
        if len(line_norm) < 10:
            continue

        similarity = SequenceMatcher(None, db_vendor, line_norm).ratio()

        if similarity >= threshold:
            return True   # ✅ MATCH FOUND

    return False


# INVOICE EXTRACTION (MINIMAL)

def extract_invoice_minimal(text, po):
    lines = text.splitlines()
    out = {}
    out["STATE"] = extract_state_from_invoice(text, po["STATE_NAME"])
    out["PO_NUMBER"] = extract_po_from_invoice_text(text, po["PO_ID"])
    out["PO_DATE"] = extract_po_date_from_pdf_matching_db(lines, po["PO_DATE"])
    out["VENDOR"] = po["VENDOR_NAME"] if vendor_match(po["VENDOR_NAME"], text) else None
    out["GSTIN"] = list(set(re.findall(r"\b\d{2}[A-Z]{5}\d{4}[A-Z][A-Z\d][Z][A-Z\d]\b", text.upper())))
    out["INVOICE_NO"] = po["INVOICE_NO"] if po["INVOICE_NO"].lower() in text.lower() else None
    out["INVOICE_DATE"] = extract_invoice_date(lines, po["PO_DATE"])
    out["_OCR_TEXT"] = text

    return out


#comapre function

def compare(po, inv):
    results = []

    # ✅ helper: never show blank in Invoice column
    def show(val):
        return val if val not in (None, "") else "NOT FOUND"

    def match(po_val, inv_val):
        if inv_val in (None, ""):
            return "MISMATCH"
        return "MATCH" if po_val == inv_val else "MISMATCH"

    # State
    results.append([
        "State",
        po["STATE_NAME"],
        show(inv["STATE"]),
        match(po["STATE_NAME"], inv["STATE"])
    ])

    # PO Number
    results.append([
        "PO Number",
        po["PO_ID"],
        show(inv["PO_NUMBER"]),
        match(po["PO_ID"], inv["PO_NUMBER"])
    ])

    # PO Date (compare only DATE, ignore time)

    po_only_date = po["PO_DATE"].date() if po["PO_DATE"] else None

    inv_only_date = (
        inv["PO_DATE"].date()
        if inv["PO_DATE"] and hasattr(inv["PO_DATE"], "date")
        else inv["PO_DATE"])

    po_date_status = (
        "MATCH"
        if po_only_date and inv_only_date and po_only_date == inv_only_date
        else "MISMATCH")

    results.append([
        "PO Date",
        po["PO_DATE"],
        show(inv["PO_DATE"]),
        po_date_status])

    # Vendor
    results.append([
        "Vendor",
        po["VENDOR_NAME"],
        show(inv["VENDOR"]),
        match(po["VENDOR_NAME"], inv["VENDOR"])
    ])

    # GSTIN
    inv_gst = inv["GSTIN"]
    invoice_val = ", ".join(inv_gst) if inv_gst else "NOT FOUND"
    status = "MATCH" if po["GST_NO"] in inv_gst else "MISMATCH"
    results.append([
        "GSTIN",
        po["GST_NO"],
        invoice_val,
        status
        ])
    
    # INVOICE NO
    results.append([
        "Invoice No",
        po["INVOICE_NO"],
        show(inv["INVOICE_NO"]),
        match(po["INVOICE_NO"], inv["INVOICE_NO"])
        ])


    # PO < Invoice
    if inv["INVOICE_DATE"] in (None, ""):
        status = "INVALID"
    else:
        status = "VALID" if po["PO_DATE"].date() < inv["INVOICE_DATE"] else "INVALID"

    results.append([
        "PO < Invoice",
        po["PO_DATE"],
        show(inv["INVOICE_DATE"]),
        status
    ])

    return results



# DB FETCH (UNCHANGED QUERY STRUCTURE)

def fetch_bulk_invoice_rows(batch_size=20):
  conn = cx_Oracle.connect("kpmg", "password", "HISTDB")
  cur = conn.cursor()

  query = """
SELECT I.PO_ID,
       I.INVOICE_NO,
       P.FILE_NAME,
       P.DOCUMENT,
       P.EXT,
       g.state_name,
       t.vendor_id,
       v.vendor_name,
       trunc(t.po_date) po_date,
       t.branch_id,
       t.total_amount,
       t.tax_type,
       g.gst_no
  FROM MANA0809.TBL_PO_INVOICE_MST@UATR_BACKUP2 I
  left join mana0809.tbl_gst_state@uatr_backup2 g
    on (i.bill_to_stid = g.gst_state_id), MANA0809.TBL_PO_MASTER@UATR_BACKUP2 T,
 DMS.TBL_CHECKLIST_DOCUMENTS@UATR_BACKUP2 P, mana0809.tbl_vendor_master@uatr_backup2 v
 WHERE I.PO_ID = P.PO_ID
   AND P.INVOICE_NO = I.INVOICE_NO
   and t.vendor_id = v.vendor_id
   and p.doc_type =3
   AND I.STATUS_ID IN (2, 7)
   AND T.PO_ID = I.PO_ID
   AND TRUNC(I.PAYMENT_DT) = TRUNC(SYSDATE-1)
  """
  cur.execute(query)
  #   AND TRUNC(I.PAYMENT_DT) = TO_DATE('27-APR-2026','DD-MON-YYYY')
# AND TRUNC(I.PAYMENT_DT) = TRUNC(SYSDATE-1)

  while True:
    rows = cur.fetchmany(batch_size)  # ✅ 20 rows at a time
    if not rows:
     break

    processed_rows = []
    for r in rows:
     r = list(r)
     if r[3]:
      r[3] = r[3].read()
     processed_rows.append(tuple(r))

    yield processed_rows  # ✅ send one batch

  cur.close()
  conn.close()

# MAIN
def main():
    print("✅ Entered main()")

    # ✅ Loop batch by batch (20 rows at a time)
    for batch in fetch_bulk_invoice_rows(batch_size=20):
        print(f"✅ New batch received: {len(batch)} invoices")

        for r in batch:
            print("➡️ Processing one invoice...")
            try:
                po = {
                    "STATE_NAME": r[5],
                    "PO_ID": r[0],
                    "PO_DATE": r[8],
                    "VENDOR_NAME": r[7],
                    "GST_NO": r[12],
                    "INVOICE_NO": r[1]
                }

                base_folder = os.path.splitext(r[2])[0]

                invoice_dir = os.path.join(BASE_DIR, base_folder)

                counter = 1
                while os.path.exists(invoice_dir):
                    invoice_dir = os.path.join(BASE_DIR, f"{base_folder}_{counter}")
                    counter += 1

                os.makedirs(invoice_dir, exist_ok=True)


                #comment below 5 lines to download all files if you want toskip already existing files then uncomment the below 5 lines
                # expected_file = os.path.join(
                # invoice_dir,
                # f"{os.path.splitext(r[2])[0]}.{r[4].lower()}")
                # if os.path.exists(expected_file):
                #     print("⏭️ File already exists, skipping:", expected_file)
                #     continue

                file_path = save_blob_file(
                    r[3], r[2], r[4].lower(), invoice_dir
                )

                if not os.path.exists(file_path):
                    print("⚠️ File missing, skipping:", file_path)
                    continue

                texts = []

                if r[4].lower() in SUPPORTED_OCR_EXT:
                    texts.append(extract_text_from_invoice(file_path))

                elif r[4].lower() == "zip":
                    for f in handle_zip(file_path):
                        texts.append(extract_text_from_invoice(f))

                text = "\n".join(texts).strip()
                print("OCR text length:", len(text))

                # ✅ Always create invoice dict
                if text:
                    invoice = extract_invoice_minimal(text, po)
                else:
                    invoice = {
                        "STATE": None,
                        "PO_NUMBER": None,
                        "PO_DATE": None,
                        "VENDOR": None,
                        "GSTIN": None,
                        "INVOICE_NO": None,
                        "INVOICE_DATE": None,
                        "_OCR_TEXT": ""
                    }

                comparison = compare(po, invoice)

                invoice_name = r[2]
                for row in comparison:
                    ALL_COMPARISONS.append([
                        po["PO_ID"],
                        row[0],
                        row[1],
                        row[2],
                        row[3]
                    ])

                print("✅ Writing Excel files for:", invoice_name)

                pd.DataFrame(invoice.items(), columns=["Field", "Invoice Value"]) \
                    .to_excel(os.path.join(invoice_dir, "invoice_extracted.xlsx"), index=False)

                pd.DataFrame(po.items(), columns=["Field", "PO Value"]) \
                    .to_excel(os.path.join(invoice_dir, "po_extracted.xlsx"), index=False)

                file_path_excel = os.path.join(invoice_dir, "comparison.xlsx")
                with pd.ExcelWriter(file_path_excel, engine='xlsxwriter') as writer:
                    df = pd.DataFrame(comparison, columns=["Field", "PO", "Invoice", "Status"])
                    # ✅ add PO column (empty initiall
                    df.insert(0, "PURCHASE ORDER ID", "")
                    # ✅ rename columns
                    df.columns = [
                        "PURCHASE ORDER ID",
                        "Field to be checked",
                        "Details as per PO",
                        "Details as per invoice",
                        "Status"
                        ]
                    # ✅ write to excel
                    df.to_excel(writer, index=False)
                    workbook = writer.book
                    worksheet = writer.sheets["Sheet1"]
                    # ✅ merge PO ID column into ONE cell vertically
                    row_count = len(df)
                    worksheet.merge_range(1, 0, row_count, 0, po["PO_ID"])


            except Exception as e:
                print("❌ Skipped invoice due to error:", e)
                continue

    combined_df = pd.DataFrame(
        ALL_COMPARISONS,
        columns=["PO_ID", "Field", "PO", "Invoice", "Status"]
    )

    # ✅ create blank PO column
    combined_df.insert(0, "PURCHASE ORDER ID", "")

    # ✅ fill PO only when it changes (like your format)
    for i in combined_df.index:
        if i % 7 == 0:
            combined_df.loc[i, "PURCHASE ORDER ID"] = combined_df.loc[i, "PO_ID"]

    # ✅ remove old PO_ID column
    combined_df = combined_df.drop(columns=["PO_ID"])

    # ✅ rename columns
    combined_df.columns = [
        "PURCHASE ORDER ID",
        "Field to be checked",
        "Details as per PO",
        "Details as per invoice",
        "Status"]

    combined_df.to_excel(os.path.join(BASE_DIR, "ALL_COMPARISONS.xlsx"), index=False)

if __name__ == "__main__":
    main()
