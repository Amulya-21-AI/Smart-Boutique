# 🛍️ Smart Boutique Management System
### Anjali Ladies Boutique — Muggam, Kozhikode, Kerala

A full-stack AI-powered boutique management system built with **Streamlit**, **SQLite**, 
and **Machine Learning** to modernize boutique operations — from order management to 
intelligent design recommendations.

---

## 📌 Project Overview

This system was developed as a Data Science & ML academic project using real-world 
boutique order data. It combines traditional database management with modern AI to 
help boutique owners make smarter business decisions.

---

## ✨ Features

### 🗄️ Core Management
- Customer registration and profile management
- Order tracking and status updates
- Tailor assignment and workload management
- Design catalog management

### 🤖 Machine Learning Models
| Model | Algorithm | Purpose |
|-------|-----------|---------|
| Return Prediction | HistGradientBoostingClassifier | Predicts if an order will be returned |
| Delivery Prediction | HistGradientBoostingRegressor | Estimates delivery time |
| Design Recommendation | GradientBoostingClassifier | Suggests designs based on customer profile |
| Demand Forecasting | GradientBoostingRegressor | Forecasts product demand |

### 🧠 Generative AI Assistant
- RAG-based AI fashion assistant
- Automated design suggestions
- Powered by a curated knowledge base (fabric guide, festival guide, product catalog)

---

## 🗂️ Project Structure
Smart-Boutique/
│
├── 📁 data/
│   ├── cleaned_data.csv            # Preprocessed Kaggle dataset
│   └── cleaned_data_ml_ready.xls  # ML-ready dataset
│
├── 📁 database/
│   ├── boutique.db                 # SQLite database
│   ├── db.py                       # Database connection & queries
│   └── schema.sql                  # Database schema
│
├── 📁 genai/
│   ├── 📁 knowledge_base/          # RAG knowledge documents
│   │   ├── fabric_guide.txt
│   │   ├── festival_guide.txt
│   │   ├── product_catalog.txt
│   │   └── size_guide.txt
│   ├── agent.py                    # AI agent logic
│   ├── memory.py                   # Conversation memory
│   └── rag_pipeline.py             # RAG implementation
│
├── main.py                         # Streamlit app entry point
├── handle_Duplicates.py            # Data cleaning utility
├── Data-preprocessing.ipynb        # EDA & preprocessing notebook
├── .gitignore
├── requirements.txt
└── README.md

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Streamlit |
| Database | SQLite |
| ML Models | scikit-learn, imbalanced-learn |
| GenAI | RAG Pipeline, ChromaDB |
| Data Processing | pandas, numpy |
| Visualization | matplotlib, seaborn |
| Language | Python 3.14 |

---

## ⚙️ Setup & Installation

### Prerequisites
- Python 3.10 or higher
- Git

### 1. Clone the Repository
```bash
git clone https://github.com/Amulya-21-AI/Smart-Boutique.git
cd Smart-Boutique
```

### 2. Create a Virtual Environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the Application
```bash
streamlit run main.py
```

---

## 📊 Dataset

- **Source:** Kaggle — Boutique Orders Dataset
- **Scope:** Women-only orders (deliberate architectural decision)
- **Size:** ~21,000 rows after preprocessing
- **Preprocessing:** Done in `Data-preprocessing.ipynb`
  - Removed duplicates
  - Filtered to women-only records
  - Handled class imbalance using RandomOverSampler (~38K rows for recommendation model)

---

## 🧪 ML Model Performance

| Model | Metric | Score |
|-------|--------|-------|
| Return Prediction | AUC | ~0.89 |
| Delivery Prediction | R² | ~0.82 |
| Design Recommendation | Accuracy | ~84% |
| Design Recommendation | Macro-F1 | ~57% |
| Demand Forecasting | R² | ~0.80 |

---

## 🔮 Future Enhancements

- [ ] WhatsApp order notification integration
- [ ] Customer-facing mobile app
- [ ] Real-time inventory tracking
- [ ] Payment gateway integration
- [ ] Multi-boutique support

---

## 👩‍💻 Developer

**Amulya** — Data Science & AI Student  
📍 Muggam, Kozhikode, Kerala  
🔗 [GitHub](https://github.com/Amulya-21-AI)

---

## 📄 License

This project is developed for academic and portfolio purposes.
