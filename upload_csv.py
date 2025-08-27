import streamlit as st
import pandas as pd
import random
import string
import os
import shutil
from datetime import datetime, timedelta
from faker import Faker

# ---------------------------- Config ----------------------------
SLIDES_FOLDER = r"D:\Slides\PathAI-Import\Uploads"  # Server folder with slides
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
    return random.randint(1000000000, 9999999999)
    #return ",".join([str(random.randint(1000000000, 9999999999)) for _ in range(n)])

def load_used_ids():
    if os.path.exists(USED_IDS_FILE):
        return pd.read_csv(USED_IDS_FILE)
    return pd.DataFrame(columns=["PatientId","AccessionId","CaseAssignees"])

def save_used_ids(df):
    df.to_csv(USED_IDS_FILE, index=False)

# ---------------------------- Streamlit App ----------------------------
st.title("Slide Upload Pipeline - Server File Selection")

# List all slide files in the server folder
all_files = [f for f in os.listdir(SLIDES_FOLDER) if f.endswith((".svs", ".ndpi"))]

# Initialize session state
if "slides" not in st.session_state:
    st.session_state.slides = [{"files": [], "algorithm": None, "specimen": None}]

case_info_dict = {}  # Track patient info by case_id

# ----------------- Dynamic slide group UI -----------------
for i, row in enumerate(st.session_state.slides):
    st.markdown(f"### Slide Group #{i+1}")
    col1, col2, col3 = st.columns([4,3,3])

    with col1:
        selected_files = st.multiselect(
            "Select slide files",
            options=all_files,
            key=f"select_{i}"
        )
        if selected_files:
            row['files'] = selected_files
        if row['files']:
            st.write("Selected files:")
            for f in row['files']:
                st.write(f)
        else:
            st.write("No files selected")

    with col2:
        row['algorithm'] = st.selectbox("Algorithm", list(TEST_DICT.keys()), key=f"alg_{i}")

    with col3:
        row['specimen'] = st.selectbox("Specimen", ["Tissue", "Biopsy"], key=f"spec_{i}")

# Add a new slide group
if st.button("Add Slide Group"):
    st.session_state.slides.append({"files": [], "algorithm": None, "specimen": None})
    st.rerun()

# ----------------- Generate CSV -----------------
if st.button("Generate Upload CSV"):
    upload_data = []
    used_ids = load_used_ids()
    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    new_folder = os.path.join(DEST_BASE_FOLDER, f"Upload_{now_str}")
    os.makedirs(new_folder, exist_ok=True)

    for row in st.session_state.slides:
        if not row['files']:
            continue

        test_name = row['algorithm']
        test_version = TEST_DICT[test_name]
        specimen_type = row['specimen']

        for file_name in row['files']:
            base_name = os.path.splitext(file_name)[0]
            parts = base_name.split("-")
            case_id = base_name[:12]

            block_id = parts[2] if len(parts) > 2 else str(random.randint(1000000,9999999))
            stain = "-".join(parts[3:]) if len(parts) > 3 else "H&E"
            test_input_name = f"{stain}_slides"

            # Reuse patient info if same case ID
            if case_id in case_info_dict:
                info = case_info_dict[case_id]
                patient_id = info["PatientId"]
                first_name = info["FirstName"]
                last_name = info["LastName"]
                patient_dob = info["PatientDob"]
            else:
                # Generate new patient info
                while True:
                    patient_id = random_patient_id()
                    if not (used_ids["PatientId"] == patient_id).any():
                        break
                first_name = faker.first_name()
                last_name = faker.last_name()
                patient_dob = random_date()

                case_info_dict[case_id] = {
                    "PatientId": patient_id,
                    "FirstName": first_name,
                    "LastName": last_name,
                    "PatientDob": patient_dob
                }
            
            # Always generate new AccessionId and CaseAssignees
            accession_id = random_accession_id()
            case_assignees = random_case_assignees()

            # Append to CSV data
            upload_data.append([
                test_name, test_version, test_input_name, patient_dob, patient_id,
                first_name, last_name, file_name, "Tissue", specimen_type, accession_id,
                stain, block_id, "", case_assignees
            ])

            # Copy slide to processed folder (optional)
            shutil.copy(os.path.join(SLIDES_FOLDER, file_name), os.path.join(new_folder, file_name))

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
