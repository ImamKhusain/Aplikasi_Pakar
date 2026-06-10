# APLIKASI_PAKAR

Aplikasi ini dibangun menggunakan Python dan Streamlit dengan penyimpanan data berbasis SQLite. Sistem menyediakan fitur login pengguna, diagnosa penyakit bayi, pengelolaan data penyakit, data gejala, rules Certainty Factor, rules Forward Chaining, serta panel admin untuk mengelola basis pengetahuan sistem.

---

# Features

- Login Authentication untuk user dan admin
- Diagnosa penyakit bayi berdasarkan gejala yang dipilih
- Penerapan metode Forward Chaining
- Penerapan metode Certainty Factor
- Input tingkat keyakinan user menggunakan skala Likert
- Perhitungan CF Pakar, CF User, dan CF Gejala
- Menampilkan hasil diagnosis utama
- Menampilkan kemungkinan penyakit lainnya
- Menampilkan detail proses Forward Chaining
- Menampilkan detail perhitungan Certainty Factor
- Menampilkan saran gejala terkait berdasarkan rule yang sesuai
- Data Penyakit
- Data Gejala
- Data Rules Certainty Factor
- Data Rules Forward Chaining
- Admin Panel untuk mengelola akun, penyakit, gejala, rules CF, dan rules Forward Chaining
- Database SQLite
- Tampilan web interaktif menggunakan Streamlit


---

# Technologies Used

- Python
- Streamlit
- Pandas
- SQLite
- Forward Chaining
- Certainty Factor
- HTML dan CSS Custom
- CSV Dataset

## Steps to Clone and Run the Project

### 1. Clone the Repository

```bash
git clone https://github.com/ImamKhusain/Aplikasi_Pakar.git
```

### 2. Open Project Folder

```bash
cd Aplikasi_Pakar
```

### 3. Create Virtual Environment

```bash
python -m venv venv
```

### 4. Activate Virtual Environment

For Windows:

```bash
venv\Scripts\activate

```

### 5. Install Dependencies

```bash
pip install streamlit pandas

```

### 6. Run Application

```bash
streamlit run app.py

```

## License
This project is created for academic purposes and can be used according to the project needs of the developer.

Happy coding! 🚀