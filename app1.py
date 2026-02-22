import streamlit as st
import math
from PIL import Image
from fpdf import FPDF

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="FC ELEC - Dimensionnement", layout="centered")

# --- 1. FONCTION DE SÉCURITÉ (LOGIN) ---
def check_password():
    """Retourne True si l'utilisateur a saisi le bon mot de passe."""
    def password_entered():
        """Vérifie les identifiants saisis dans les secrets Streamlit."""
        if st.session_state["username"] in st.secrets["passwords"] and \
           st.session_state["password"] == st.secrets["passwords"][st.session_state["username"]]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.image("logoFCELEC.png", width=250)
        st.title("🔐 Accès Restreint FC ELEC")
        st.text_input("Nom d'utilisateur", on_change=password_entered, key="username")
        st.text_input("Mot de passe", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.image("logoFCELEC.png", width=250)
        st.error("Utilisateur inconnu ou mot de passe incorrect.")
        st.text_input("Nom d'utilisateur", on_change=password_entered, key="username")
        st.text_input("Mot de passe", type="password", on_change=password_entered, key="password")
        return False
    else:
        return True

# --- 2. CONDITION D'AFFICHAGE DU CONTENU ---
if check_password():
    
    # Barre latérale de déconnexion
    st.sidebar.image("logoFCELEC.png", use_container_width=True)
    st.sidebar.success(f"Connecté ✅")
    if st.sidebar.button("Se déconnecter"):
        st.session_state.clear()
        st.rerun()

    st.title("⚡ Simulateur de Dimensionnement NF C 15-100")
    
    # --- AJOUT RÉFÉRENCE DE CIRCUIT ---
    st.subheader("📋 Identification")
    col_ref1, col_ref2 = st.columns(2)
    with col_ref1:
        nom_projet = st.text_input("Nom du Projet / Client", "Chantier Client")
    with col_ref2:
        ref_circuit = st.text_input("Référence du Circuit", "DEPART_01")
    
    st.markdown("---")

    # --- 3. ENTRÉES UTILISATEUR ---
    col_input1, col_input2 = st.columns(2)
    
    with col_input1:
        tension_type = st.radio("Tension", ["Monophasé (230V)", "Triphasé (400V)"])
        nature_cable = st.selectbox("Nature du conducteur", ["Cuivre", "Aluminium"])
        longueur = st.number_input("Longueur du câble (m)", min_value=1, value=50)

    with col_input2:
        mode_saisie = st.radio("Saisie par", ["Puissance (W)", "Courant (A)"])
        if mode_saisie == "Puissance (W)":
            P = st.number_input("Puissance (Watts)", value=3500)
            cos_phi = st.slider("cos φ", 0.7, 1.0, 0.85)
        else:
            Ib_input = st.number_input("Courant Ib (Ampères)", value=16.0)
            cos_phi = 0.85

    delta_u_max_pct = st.select_slider("Chute de tension max (%)", options=[3, 5, 8], value=3)

    # --- 4. CALCULS TECHNIQUES ---
    V = 230 if tension_type == "Monophasé (230V)" else 400
    rho = 0.0225 if nature_cable == "Cuivre" else 0.036
    b = 2 if tension_type == "Monophasé (230V)" else 1

    if mode_saisie == "Puissance (W)":
        if tension_type == "Monophasé (230V)":
            Ib = P / (V * cos_phi)
        else:
            Ib = P / (V * math.sqrt(3) * cos_phi)
    else:
        Ib = Ib_input

    calibres = [10, 16, 20, 25, 32, 40, 50, 63, 80, 100, 125, 160, 200, 250, 400, 630]
    In = next((x for x in calibres if x >= Ib), calibres[-1])

    delta_u_limite_v = (delta_u_max_pct / 100) * V
    S_calculée = (b * rho * longueur * Ib) / delta_u_limite_v
    
    sections_std = [1.5, 2.5, 4, 6, 10, 16, 25, 35, 50, 70, 95, 120, 150, 185, 240]
    S_retenue = next((s for s in sections_std if s >= S_calculée), sections_std[-1])

    du_v = (b * rho * longueur * Ib) / S_retenue
    du_pct = (du_v / V) * 100

    # --- 5. RÉSULTATS ÉCRAN ---
    st.markdown("### 📊 Résultats du dimensionnement")
    res1, res2, res3 = st.columns(3)
    res1.metric("Courant Ib", f"{Ib:.2f} A")
    res2.metric("Disjoncteur In", f"{In} A")
    res3.metric("Section retenue", f"{S_retenue} mm²")

    if du_pct > delta_u_max_pct:
        st.error(f"Attention : Chute de tension de {du_pct:.2f}% (Seuil de {delta_u_max_pct}% dépassé)")
    else:
        st.success(f"Chute de tension conforme : {du_pct:.2f}% ({du_v:.2f} V)")

    # --- 6. GÉNÉRATION PDF (SYNTHÈSE SANS DÉTAILS) ---
    def generate_pdf():
        pdf = FPDF()
        pdf.add_page()
        
        # En-tête
        try:
            pdf.image("logoFCELEC.png", 10, 8, 35)
        except:
            pass
        
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(190, 15, "NOTE DE SYNTHESE ELECTRIQUE", ln=True, align="C")
        pdf.ln(10)

        # Bloc Projet
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(190, 10, f" PROJET : {nom_projet.upper()}", border=1, ln=True, fill=True)
        pdf.cell(190, 10, f" REFERENCE CIRCUIT : {ref_circuit}", border=1, ln=True)
        pdf.ln(5)

        # Tableau de synthèse
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(100, 10, "CARACTERISTIQUE", border=1, align="C")
        pdf.cell(90, 10, "VALEUR", border=1, ln=True, align="C")
        
        pdf.set_font("Helvetica", "", 11)
        lignes = [
            ("Tension de service", f"{tension_type}"),
            ("Nature du conducteur", f"{nature_cable}"),
            ("Longueur de liaison", f"{longueur} m"),
            ("Intensite d'emploi (Ib)", f"{Ib:.2f} A"),
            ("Protection conseillee (In)", f"{In} A"),
            ("Chute de tension reelle", f"{du_pct:.2f} %"),
            ("SECTION DE CABLE RETENUE", f"{S_retenue} mm2")
        ]

        for desc, val in lignes:
            if "SECTION" in desc:
                pdf.set_font("Helvetica", "B", 12)
                pdf.set_text_color(255, 140, 0) # Couleur Orange FC ELEC
            pdf.cell(100, 10, f" {desc}", border=1)
            pdf.cell(90, 10, f" {val}", border=1, ln=True, align="C")
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Helvetica", "", 11)

        pdf.ln(15)
        pdf.set_font("Helvetica", "I", 8)
        pdf.cell(190, 10, "Document genere par FC ELEC conforme a la norme NF C 15-100", align="C")
        
        return pdf.output()

    st.markdown("---")
    if st.button("📄 Préparer la Note de Calcul (PDF)"):
        pdf_bytes = generate_pdf()
        st.download_button(
            label="📥 Télécharger le PDF",
            data=bytes(pdf_bytes),
            file_name=f"FCELEC_{ref_circuit}.pdf",
            mime="application/pdf"
        )

    st.info("💡 Ce calcul est basé sur la chute de tension. Vérifiez l'intensité admissible (Iz) selon le mode de pose.")