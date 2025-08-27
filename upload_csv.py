import streamlit as st
import pandas as pd
import random
import string
import os
import shutil
from datetime import datetime, timedelta
from tkinter import Tk, filedialog
from faker import Faker

# ---------------------------- Config ----------------------------
DEST_BASE_FOLDER = r"D:\Slides\PathAI-Import\Processed"
USED_IDS_FILE = "used_ids.csv"

TEST_DICT = {
    "AIM-ER Breast": "1.0.0",
    "AIM-HER2 Breast": "1.1.0",
    "AIM-Ki-67 Breast": "1.0.0",
    "AIM-NASH": "1.0.5",
    "AIM-PD-L1 NSCLC": "2.0.2",
    "AIM-PR Breast": "1.0.0",
    "AIM-TumorCellularity": "2.0.0",
    "DeepDx Prostate (RUO)": "2.0.0",
    "Manual Review": "Manual Review",
    "Paige Prostate Detect": "2.1.1",
    "PathAssist Derm": "1.0.0",
    "TumorDetect": "1.2.0"
}

faker = Faker()

# ---------------------------- Utility Functions ----------------------------
def random_date(start_year=1940, end_year=2015):
    start = datetime(start_year, 1, 1)
    end = datetime(end_year, 12, 31)
    return (start + timedelta(days=random.randint(0, (end-start).days))).strftime("%Y-%m-%d")

def random_patient_id():
    return random.choice(string.ascii_uppercase) + str(random.randint(1000, 9999))

def random_accession_id():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=10))

def random_case_assignees(n=2):
    return ",".join([str(random.randint(1000000000, 9999999999)) for _ in range(n)])

def load_used_ids():
    if os.path.exists(USED_IDS_FILE):
        return pd.read_csv(USED_IDS_FILE)
    return pd.DataFrame(columns=["PatientId","AccessionId","CaseAssignees"])

def save_used_ids(df):
    df.to_csv(USED_IDS_FILE, index=False)

def browse_files():
    root = Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    file_paths = filedialog.askopenfilenames(filetypes=[("Slide Files", "*.svs *.ndpi")])
    root.destroy()
    return list(file_paths)

# ---------------------------- Streamlit App ----------------------------
st.title("Slide Upload Pipeline - Path Only")

# Initialize session state
if "slides" not in st.session_state:
    st.session_state.slides = [{"file_path": [], "algorithm": None, "specimen": None}]

# Dictionary to track case info in memory
case_info_dict = {}

# ----------------- Dynamic slide group UI -----------------
for i, row in enumerate(st.session_state.slides):
    st.markdown(f"### Slide Group #{i+1}")
    col1, col2, col3 = st.columns([4,3,3])

    with col1:
        if st.button("Select File(s)", key=f"browse_{i}"):
            file_paths = browse_files()
            if file_paths:
                row['file_path'] = file_paths
        if row['file_path']:
            st.write("Selected files:")
            for f in row['file_path']:
                st.write(os.path.basename(f))
        else:
            st.write("No files selected")

    with col2:
        row['algorithm'] = st.selectbox("Algorithm", list(TEST_DICT.keys()), key=f"alg_{i}")

    with col3:
        row['specimen'] = st.selectbox("Specimen", ["Tissue", "Biopsy"], key=f"spec_{i}")

# Add a new slide group
if st.button("Add Slide Group"):
    st.session_state.slides.append({"file_path": [], "algorithm": None, "specimen": None})
    st.rerun()

# ----------------- Generate CSV -----------------
if st.button("Generate Upload CSV"):
    upload_data = []
    used_ids = load_used_ids()
    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    new_folder = os.path.join(DEST_BASE_FOLDER, f"Upload_{now_str}")
    os.makedirs(new_folder, exist_ok=True)

    for row in st.session_state.slides:
        if not row['file_path']:
            continue

        test_name = row['algorithm']
        test_version = TEST_DICT[test_name]
        specimen_type = row['specimen']

        for file_path in row['file_path']:
            file_name = os.path.basename(file_path)
            base_name = os.path.splitext(file_name)[0]
            parts = base_name.split("-")

            # Extract case ID from filename (first 12 chars)
            case_id = base_name[:12]

            # Extract block ID and stain
            block_id = parts[2] if len(parts) > 2 else str(random.randint(1000000,9999999))
            stain = "-".join(parts[3:]) if len(parts) > 3 else "H&E"
            test_input_name = f"{stain}_slides"

            # Reuse patient info if same case ID
            if case_id in case_info_dict:
                info = case_info_dict[case_id]
                patient_id = info["PatientId"]
                accession_id = info["AccessionId"]
                case_assignees = info["CaseAssignees"]
                first_name = info["FirstName"]
                last_name = info["LastName"]
                patient_dob = info["PatientDob"]
            else:
                # Generate new patient info
                while True:
                    patient_id = random_patient_id()
                    accession_id = random_accession_id()
                    case_assignees = random_case_assignees()
                    if not ((used_ids["PatientId"] == patient_id).any() or
                            (used_ids["AccessionId"] == accession_id).any() or
                            (used_ids["CaseAssignees"] == case_assignees).any()):
                        break
                first_name = faker.first_name()
                last_name = faker.last_name()
                patient_dob = random_date()

                # Store for future reuse
                case_info_dict[case_id] = {
                    "PatientId": patient_id,
                    "AccessionId": accession_id,
                    "CaseAssignees": case_assignees,
                    "FirstName": first_name,
                    "LastName": last_name,
                    "PatientDob": patient_dob
                }

            # Append to CSV data
            upload_data.append([
                test_name, test_version, test_input_name, patient_dob, patient_id,
                first_name, last_name, file_name, "Tissue", specimen_type, accession_id,
                stain, block_id, "", case_assignees
            ])

            # Copy slide to processed folder
            shutil.copy(file_path, os.path.join(new_folder, file_name))

    # Save CSV
    columns = ["Test Name","Test Version","Test Input Name","Patient Dob","Patient Id",
               "First Name","Last Name","Slide File Name","Specimen","Specimen Type",
               "Accession Id","Stain","Block Id","Replace","Case Assignees"]
    df = pd.DataFrame(upload_data, columns=columns)
    csv_path = os.path.join(new_folder, f"upload_file_{now_str}.csv")
    df.to_csv(csv_path, index=False)
    save_used_ids(used_ids)

    st.success(f"✅ Upload CSV & slide copies generated in folder: {new_folder}")
    st.dataframe(df)
