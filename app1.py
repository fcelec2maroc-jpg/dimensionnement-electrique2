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
            del st.session_state["password"]  # Sécurité : on efface le MDP
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # Premier affichage : Formulaire de login
        st.image("logoFCELEC.png", width=250)
        st.title("🔐 Accès Restreint FC ELEC")
        st.text_input("Nom d'utilisateur", on_change=password_entered, key="username")
        st.text_input("Mot de passe", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        # En cas d'erreur de saisie
        st.image("logoFCELEC.png", width=250)
        st.error("Utilisateur inconnu ou mot de passe incorrect.")
        st.text_input("Nom d'utilisateur", on_change=password_entered, key="username")
        st.text_input("Mot de passe", type="password", on_change=password_entered, key="password")
        return False
    else:
        # Accès validé
        return True

# --- 3. EXÉCUTION DU CALCULATEUR SI CONNECTÉ ---
if check_password():
    # Barre latérale
    st.sidebar.image("logoFCELEC.png", use_container_width=True)
    if st.sidebar.button("Se déconnecter"):
        st.session_state.clear()
        st.rerun()

    st.title("⚡ Calculateur de Liaison Électrique")

    # --- IDENTIFICATION ---
    st.subheader("📋 Références du dossier")
    col_ref1, col_ref2 = st.columns(2)
    with col_ref1:
        nom_projet = st.text_input("Nom du Projet / Client", "Chantier Client")
    with col_ref2:
        ref_circuit = st.text_input("Référence du Circuit", "DEPART_01")

    st.divider()

    # --- ENTRÉES TECHNIQUES ---
    c1, c2 = st.columns(2)
    with c1:
        tension = st.radio("Tension de service", ["230V Monophasé", "400V Triphasé"])
        nature = st.selectbox("Nature du conducteur", ["Cuivre", "Aluminium"])
        longueur = st.number_input("Longueur de la liaison (m)", min_value=1, value=50)
    
    with c2:
        mode = st.radio("Mode de saisie de la charge", ["Puissance (W)", "Courant (A)"])
        valeur = st.number_input("Valeur", min_value=1.0, value=3500.0)
        cos_phi = st.slider("Facteur de puissance (cos φ)", 0.7, 1.0, 0.85)
        du_max = st.selectbox("Chute de tension max (%)", [3, 5, 8])

    # --- CALCULS INTERNES ---
    V = 230 if "230V" in tension else 400
    rho = 0.0225 if nature == "Cuivre" else 0.036
    b = 2 if "230V" in tension else 1

    if mode == "Puissance (W)":
        if b == 2: Ib = valeur / (V * cos_phi)
        else: Ib = valeur / (V * math.sqrt(3) * cos_phi)
    else:
        Ib = valeur

    calibres = [10, 16, 20, 25, 32, 40, 50, 63, 80, 100, 125, 160, 200, 250, 400, 630]
    In = next((x for x in calibres if x >= Ib), calibres[-1])

    S_calc = (b * rho * longueur * Ib) / ((du_max/100)*V)
    sections_std = [1.5, 2.5, 4, 6, 10, 16, 25, 35, 50, 70, 95, 120, 150, 185, 240]
    S_retenue = next((s for s in sections_std if s >= S_calc), sections_std[-1])

    du_v = (b * rho * longueur * Ib) / S_retenue
    du_pct = (du_v / V) * 100

    # --- RÉSULTATS À L'ÉCRAN ---
    st.markdown("---")
    st.subheader("📊 Résultats du dimensionnement")
    res1, res2, res3 = st.columns(3)
    res1.metric("Courant Ib", f"{Ib:.2f} A")
    res2.metric("Protection In", f"{In} A")
    res3.metric("Section retenue", f"{S_retenue} mm²")

    # --- GÉNÉRATION DU PDF (SYNTHÈSE SANS DÉTAILS) ---
    def generate_pdf():
        pdf = FPDF()
        pdf.add_page()
        
        # Logo & Titre
        try:
            pdf.image("logoFCELEC.png", 10, 8, 35)
        except:
            pass
        
        pdf.set_font("Arial", "B", 16)
        pdf.cell(190, 15, "NOTE DE SYNTHESE ELECTRIQUE", ln=True, align="C")
        pdf.ln(10)

        # Bloc Identification
        pdf.set_font("Arial", "B", 11)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(190, 10, f" PROJET : {nom_projet.upper()}", border=1, ln=True, fill=True)
        pdf.cell(190, 10, f" REFERENCE CIRCUIT : {ref_circuit}", border=1, ln=True)
        pdf.ln(5)

        # Tableau des résultats
        pdf.set_font("Arial", "B", 11)
        pdf.cell(100, 10, "DESIGNATION", border=1, align="C")
        pdf.cell(90, 10, "VALEUR", border=1, ln=True, align="C")
        
        pdf.set_font("Arial", "", 11)
        lignes = [
            ("Tension de service", f"{tension}"),
            ("Nature du conducteur", f"{nature}"),
            ("Longueur de liaison", f"{longueur} m"),
            ("Intensite d'emploi (Ib)", f"{Ib:.2f} A"),
            ("Protection conseillee (In)", f"{In} A"),
            ("Chute de tension reelle", f"{du_pct:.2f} % ({du_v:.2f} V)"),
            ("SECTION DE CABLE RETENUE", f"{S_retenue} mm2")
        ]

        for desc, val in lignes:
            if "SECTION" in desc:
                pdf.set_font("Arial", "B", 12)
                pdf.set_text_color(255, 100, 0) # Couleur distinctive pour la section
            pdf.cell(100, 10, f" {desc}", border=1)
            pdf.cell(90, 10, f" {val}", border=1, ln=True, align="C")
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("Arial", "", 11)

        pdf.ln(20)
        pdf.set_font("Arial", "I", 9)
        pdf.multi_cell(190, 5, "Note : Ce document presente les conclusions techniques de dimensionnement conformement a la norme NF C 15-100.", align="C")
        
        return pdf.output(dest='S').encode('latin-1')

    # Bouton PDF
    st.write(" ")
    if st.button("📄 Préparer la Note de Calcul (PDF)"):
        pdf_bytes = generate_pdf()
        st.download_button(
            label="📥 Télécharger le fichier PDF",
            data=pdf_bytes,
            file_name=f"FCELEC_{ref_circuit}.pdf",
            mime="application/pdf"
        )

# --- FIN DU CODE ---