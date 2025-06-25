import streamlit as st
import json
import os
import random
import pandas as pd
import time

DATA_FILE = "swedish_words.json"
COOLDOWN_SECONDS = 300
ADMIN_PASSWORD = st.secrets.get("admin_password", "")
LABELS = ["0%", "25%", "50%", "75%", "100%"]


def load_words():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        words = json.load(f)
    for w in words:
        if "label" not in w:
            w["label"] = "0%"
        if "seen" not in w:
            w["seen"] = 0
    save_words(words)
    return words


def save_words(words):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(words, f, indent=2, ensure_ascii=False)


def word_exists(swedish_word):
    words = load_words()
    return any(w["swedish"].lower() == swedish_word.lower() for w in words)


def add_word(swedish, english, category):
    if word_exists(swedish):
        return False
    words = load_words()
    words.append({
        "swedish": swedish,
        "english": english,
        "label": "0%",
        "category": category,
        "seen": 0
    })
    save_words(words)
    return True


def select_random_mixture(words, ratios):
    result = []
    pool = [w for w in words if w["label"] in ratios]
    for label, ratio in ratios.items():
        lw = [w for w in pool if w["label"] == label]
        count = max(1, int(len(pool) * ratio))
        result.extend(random.sample(lw, min(len(lw), count)))
    random.shuffle(result)
    return result


def render_flashcard(word, show_translation=False):
    st.markdown(f"""
    <div style="border: 2px solid #ccc; border-radius: 10px; padding: 40px; text-align: center; background-color: white; box-shadow: 2px 2px 10px rgba(0,0,0,0.1);">
        <h2>{word['swedish']}</h2>
        {"<hr /><p style='font-size:20px;'>" + word['english'] + "</p>" if show_translation else ""}
    </div>
    """, unsafe_allow_html=True)


def reset_all_labels(words):
    for word in words:
        word["label"] = "0%"
    save_words(words)


def reset_all_seen(words):
    for word in words:
        word["seen"] = 0
    save_words(words)


def group_by_seen(words):
    grouped = {
        "Low (0–2)": [],
        "Medium (3–5)": [],
        "High (6+)": []
    }
    for word in words:
        if word["seen"] <= 2:
            grouped["Low (0–2)"].append(word)
        elif word["seen"] <= 5:
            grouped["Medium (3–5)"].append(word)
        else:
            grouped["High (6+)"].append(word)
    return grouped


def main():
    st.set_page_config(page_title="Swedish Flashcards", layout="centered")
    st.title("📘 Swedish Flashcard App")

    menu = st.sidebar.radio("Choose action", [
      "🧠 Learn New Words (Random)",
      "📂 Flashcards by Category",
      "🔁 English to Swedish Mode",  # ← New menu option
      "➕ Add New Word",
      "📖 View All Words",
      "🛠️ Admin Panel"
    ])


    words = load_words()

    if "recently_seen" not in st.session_state:
        st.session_state.recently_seen = {}

    if "ratios" not in st.session_state:
        st.session_state.ratios = {
            "0%": 0.6,
            "25%": 0.2,
            "50%": 0.15,
            "75%": 0.0,
            "100%": 0.05
        }

    if menu == "🧠 Learn New Words (Random)":
        st.header("Flashcard Training")
        now = time.time()
        st.session_state.recently_seen = {
            w: t for w, t in st.session_state.recently_seen.items()
            if now - t < COOLDOWN_SECONDS
        }

        available_words = [
            w for w in select_random_mixture(words, st.session_state.ratios)
            if w["swedish"] not in st.session_state.recently_seen
        ]

        if "current_word" not in st.session_state:
            st.session_state.current_word = None
            st.session_state.reveal = False

        if st.button("🔀 Draw New Word"):
            if available_words:
                selected = random.choice(available_words)
                selected["seen"] += 1
                save_words(words)
                st.session_state.current_word = selected
                st.session_state.reveal = False
                st.session_state.recently_seen[selected["swedish"]] = now
            else:
                st.warning("⚠️ No new words available right now. Please wait 5 minutes or add more.")

        if st.session_state.current_word:
            render_flashcard(st.session_state.current_word, st.session_state.reveal)
            if not st.session_state.reveal:
                show = st.button("👁️ Show Translation")
                if show:
                    st.session_state.reveal = True
                    st.rerun()

    elif menu == "📂 Flashcards by Category":
        st.header("Flashcards by Category")
        categories = sorted(set(w["category"] for w in words if "category" in w))
        selected_category = st.selectbox("Choose a category", categories)

        filtered_words = [w for w in words if w["category"] == selected_category]
        if st.button("🔀 Draw Word from Category"):
            if filtered_words:
                selected = random.choice(filtered_words)
                st.session_state.current_word = selected
                st.session_state.reveal = False
                selected["seen"] += 1
                save_words(words)
            else:
                st.warning("⚠️ No words in this category.")

        if "current_word" in st.session_state and st.session_state.current_word:
            render_flashcard(st.session_state.current_word, st.session_state.reveal)
            if not st.session_state.reveal:
                if st.button("👁️ Show Translation"):
                    st.session_state.reveal = True
                    st.rerun()

    elif menu == "➕ Add New Word":
        st.header("Add a New Word")
        swedish = st.text_input("Swedish Word")
        english = st.text_input("English Meaning")
        category = st.text_input("Category (e.g., at home, in the office)")
        if st.button("Add Word"):
            if swedish and english and category:
                if add_word(swedish, english, category):
                    st.success(f"✅ Added '{swedish}' successfully!")
                else:
                    st.error(f"⚠️ The word '{swedish}' already exists.")
            else:
                st.warning("Please fill in all fields.")

    elif menu == "📖 View All Words":
        st.header("📚 All Words in Dictionary")
        if words:
            df = pd.DataFrame(words)
            df = df[["swedish", "english", "category", "label", "seen"]]
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No words added yet.")

    elif menu == "🛠️ Admin Panel":
        st.header("🔐 Admin Access")
        admin_password = st.text_input("Enter admin password", type="password")

        if admin_password != ADMIN_PASSWORD:
            st.warning("Incorrect password.")
        else:
            st.success("Access granted!")

            st.subheader("📊 Adjust Label Ratios (Sum should be ≤ 1.0)")
            total_ratio = 0
            for label in LABELS:
                if label not in st.session_state.ratios:
                    st.session_state.ratios[label] = 0.0
                st.session_state.ratios[label] = st.number_input(
                    f"Ratio for {label}",
                    min_value=0.0,
                    max_value=1.0,
                    value=st.session_state.ratios[label],
                    step=0.01,
                    key=f"ratio_{label}"
                )
                total_ratio += st.session_state.ratios[label]
            st.markdown(f"**Total Ratio: {total_ratio:.2f}**")

            col1, col2 = st.columns(2)
            if col1.button("🔁 Reset All Labels to 0%"):
                reset_all_labels(words)
                st.success("All word labels have been reset to 0%!")
                st.rerun()
            if col2.button("🔁 Reset All Seen Counts to 0"):
                reset_all_seen(words)
                st.success("All 'seen' counters have been reset to 0!")
                st.rerun()

            st.subheader("📦 Bulk Update Words")

            st.markdown("**Filter by Label and Set New Label**")
            selected_labels = st.multiselect("Select current labels", LABELS)
            new_bulk_label = st.selectbox("New label for selected words", LABELS)
            st.markdown("**OR: Filter by Seen Count and Set New Seen Value**")
            min_seen = st.slider("Minimum 'seen'", 0, 20, 0)
            max_seen = st.slider("Maximum 'seen'", 0, 20, 10)
            new_seen_value = st.slider("Set new 'seen' value", 0, 20, 0)

            selected_indices = []
            for idx, word in enumerate(words):
                label_match = not selected_labels or word["label"] in selected_labels
                seen_match = min_seen <= word["seen"] <= max_seen
                if label_match or seen_match:
                    is_selected = st.checkbox(
                        f"{word['swedish']} ({word['label']}, seen: {word['seen']})", key=f"select_{idx}"
                    )
                    if is_selected:
                        selected_indices.append(idx)

            if st.button("✅ Apply Label and Seen Value to Selected"):
                for idx in selected_indices:
                    words[idx]["label"] = new_bulk_label
                    words[idx]["seen"] = new_seen_value
                save_words(words)
                st.success("Updated selected word labels and seen values.")
                st.rerun()
    

    elif menu == "🔁 English to Swedish Mode":
        st.header("English to Swedish Flashcard Training")
        now = time.time()
        st.session_state.recently_seen = {
            w: t for w, t in st.session_state.recently_seen.items()
            if now - t < COOLDOWN_SECONDS
        }

        available_words = [
            w for w in select_random_mixture(words, st.session_state.ratios)
            if w["english"] not in st.session_state.recently_seen
        ]

        if st.button("🔀 Draw English Word"):
            if available_words:
                selected = random.choice(available_words)
                selected["seen"] += 1
                save_words(words)
                st.session_state.current_word = selected
                st.session_state.reveal = False
                st.session_state.recently_seen[selected["english"]] = now
            else:
                st.warning("⚠️ No new words available right now. Please wait 5 minutes or add more.")

        if "current_word" in st.session_state and st.session_state.current_word:
            word = st.session_state.current_word
            st.markdown(f"""
            <div style="border: 2px solid #ccc; border-radius: 10px; padding: 40px; text-align: center; background-color: white; box-shadow: 2px 2px 10px rgba(0,0,0,0.1);">
                <h2>{word['english']}</h2>
                {"<hr /><p style='font-size:20px;'>" + word['swedish'] + "</p>" if st.session_state.reveal else ""}
            </div>
            """, unsafe_allow_html=True)

            if not st.session_state.reveal:
                if st.button("👁️ Reveal Swedish"):
                    st.session_state.reveal = True
                    st.rerun()


if __name__ == "__main__":
    main()
