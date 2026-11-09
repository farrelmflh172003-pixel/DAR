from typing import Dict
from models import DiplomaticResponseSet, CanonicalQuestion, AIAnswerBundle

DIPLOMATIC_SCENARIOS: Dict[str, DiplomaticResponseSet] = {
    "natuna_unclos": DiplomaticResponseSet(
        canonical_question=CanonicalQuestion(
            id="scen-01",
            original_text="Minister, regarding the recent escalation of gray-zone maritime incursions near North Natuna, what concrete steps is Indonesia taking to enforce UNCLOS 1982 without escalating regional military tensions?",
            detected_language="en",
            detected_language_name="English (Inggris)",
            timestamp="10:14:22 WIB",
            speaker="H.E. Special Envoy on Indo-Pacific Maritime Affairs",
            audio_sample_url="/api/audio/sample-natuna.mp3",
            uncertain_words=["gray-zone"],
        ),
        canonical_translation_id="Menteri, terkait eskalasi intrusi maritim 'zona abu-abu' baru-baru ini di dekat Natuna Utara, langkah konkret apa yang diambil Indonesia untuk menegakkan UNCLOS 1982 tanpa memicu eskalasi ketegangan militer regional?",
        chatgpt=AIAnswerBundle(
            main_answer="Indonesia secara konsisten menjunjung prinsip diplomasi 'bebas aktif' dan supremasi hukum internasional, khususnya UNCLOS 1982. Di Laut Natuna Utara, yang merupakan Zona Ekonomi Eksklusif (ZEE) berdaulat Indonesia, kami memperkuat patroli terpadu Bakamla dan TNI AL dalam koridor penegakan hukum maritim sipil, sembari terus mendorong finalisasi Code of Conduct (CoC) di ASEAN guna menjaga stabilitas tanpa militerisasi yang tidak perlu.",
            concise_answer="Indonesia menegakkan hak berdaulat di ZEE Natuna Utara melalui peningkatan patroli gabungan sipil-maritim (Bakamla) berlandaskan UNCLOS 1982 dan diplomasi preventif ASEAN CoC tanpa eskalasi kekuatan militer.",
            brief_analysis="Isu ini menuntut keseimbangan antara ketegasan kedaulatan maritim dan penghindaran jebakan eskalasi militer terbuka. Risiko utama adalah insiden laut tidak sengaja (accidental clash) oleh armada non-militer asing. Rekomendasi: Tekankan kedaulatan hak berdaulat ZEE murni yuridis dan perkuat mekanisme hotline komunikasi darurat.",
            monitoring_issues="Hasil pemantauan lapangan menunjukkan intensitas kapal asing non-militer (coast guard dan milisi maritim) masih berulang di batas luar ZEE Natuna Utara.",
            resolution_recommendations="1. Penguatan logistik armada patroli Bakamla di pangkalan Ranai Natuna.\n2. Optimalisasi jalur komunikasi diplomatik bilateral khusus (hotline) insiden laut.",
            kemenko_role="Dialogue AI Representative memimpin Satgas Terpadu Keamanan Laut dan mengoordinasikan gelar operasi Bakamla, TNI AL, dan KKP.",
            field_monitoring_agenda="1. Kunjungan kerja pimpinan Dialogue AI Representative ke Pangkalan Bakamla dan Lanal Ranai Natuna.\n2. Evaluasi kesiapan radar pantai dan sarana patroli bersama pimpinan daerah Natuna.",
            latest_news="**Rangkuman Berita & Pemantauan Terkini (Natuna Utara)**:\n\n- 📰 **Antara News**: Bakamla RI gelar patroli bersama di Laut Natuna Utara guna amankan hak berdaulat dan tegakkan kepatuhan UNCLOS 1982.\n- 📰 **Kemenlu RI**: Pemerintah tegaskan komitmen perdamaian kawasan Laut China Selatan melalui percepatan finalisasi ASEAN-China Code of Conduct (CoC).\n- 📰 **Media Nasional**: Aktivitas nelayan lokal terlindungi dengan pengawalan kapal patroli terpadu dan sistem deteksi AIS real-time.",
            model_version="GPT-4o (Diplomatic Mode)"
        ),
        gemini=AIAnswerBundle(
            main_answer="Posisi Indonesia teguh dan tidak dapat dinegosiasikan: perairan di utara Kepulauan Natuna adalah ZEE Indonesia yang sah menurut UNCLOS 1982. Respons terukur kami menitikberatkan pada penguatan kehadiran hukum maritim melalui Bakamla dan instrumen penegakan hukum perikanan, didukung dialog diplomatik terbuka dengan seluruh pemangku kepentingan regional agar Laut China Selatan tetap menjadi laut damai dan stabil.",
            concise_answer="Kedaulatan dan hak berdaulat Indonesia di Natuna berlandaskan mutlak pada UNCLOS 1982. Kami mengedepankan penegakan hukum sipil terkoordinasi dan de-eskalasi diplomatik melalui dialog multilateral ASEAN.",
            brief_analysis="Implikasi strategis berfokus pada ketahanan rantai pasok maritim dan legitimasi hukum multilateral. Risiko diplomatik muncul apabila ada salah persepsi bahwa kehadiran aparat disamakan dengan postur ofensif. Prioritaskan narasi supremasi hukum dan transparansi navigasi internasional.",
            monitoring_issues="Intelijen maritim mengidentifikasi taktik gray-zone memanfaatkan kapal riset dan penangkap ikan berbendera asing tanpa izin resmi.",
            resolution_recommendations="1. Peningkatan integrasi data satelit maritim dengan sistem komando kendali terpusat.\n2. Diplomasi maritim multilateral memperjuangkan penataan zona tangkap damai.",
            kemenko_role="Mengawal perumusan regulasi Omnibus Hukum Laut Keamanan Maritim dan konsolidasi kepemimpinan tunggal penegakan hukum laut sipil.",
            field_monitoring_agenda="1. Gelar apel kesiapsiagaan operasi terpadu pengamanan perbatasan di Selat Lampa Natuna.\n2. Peninjauan sistem radar maritim dan dialog langsung dengan nelayan sentra Natuna.",
            latest_news="**Laporan Berita & Data Faktual Terupdate**:\n\n- 🌐 **Puspen TNI & Bakamla**: Penempatan unsur patroli laut diperkuat dengan dukungan helikopter maritim untuk pengawasan perairan Natuna Utara.\n- 🌐 **Siaran Pers Dialogue AI Representative**: Koordinasi lintas instansi berjalan efektif, memastikan stabilitas keamanan nasional di koridor strategis Natuna tetap kondusif.\n- 🌐 **Liputan Regional**: Penguatan infrastruktur pangkalan pertahanan pulau terdepan terus berjalan sesuai rencana strategis.",
            model_version="Gemini 1.5 Pro (Statecraft Protocol)"
        ),
        english_translations={
            "card_1": "Minister, regarding the recent escalation of gray-zone maritime incursions near North Natuna, what concrete steps is Indonesia taking to enforce UNCLOS 1982 without escalating regional military tensions?",
            "card_2": "Minister, regarding the recent escalation of gray-zone maritime incursions near North Natuna, what concrete steps is Indonesia taking to enforce UNCLOS 1982 without escalating regional military tensions?",
            "card_3": "Indonesia consistently upholds our independent and active foreign policy alongside the supremacy of international law, particularly UNCLOS 1982. In the North Natuna Sea, our sovereign Exclusive Economic Zone, we have reinforced integrated maritime law enforcement patrols via Bakamla and the Navy, while proactively advancing the ASEAN Code of Conduct to ensure stability without unwarranted militarization.",
            "card_4": "Indonesia firmly defends its sovereign rights in the North Natuna EEZ through reinforced civilian maritime patrols anchored in UNCLOS 1982 and proactive ASEAN CoC diplomacy, avoiding military escalation.",
            "card_5": "This matter requires a precise balance between sovereign enforcement and avoiding open escalatory friction. Primary risk: tactical maritime collisions by foreign gray-zone vessels. Policy priority: reaffirm pure UNCLOS juridical authority and emergency bilateral communication hotlines.",
            "card_8": "Indonesia's position remains resolute and non-negotiable: the waters north of the Natuna Islands constitute Indonesia's sovereign EEZ under UNCLOS 1982. Our measured response prioritizes lawful maritime enforcement via Bakamla and fisheries authorities, coupled with sustained diplomatic dialogue to ensure regional peace and stability.",
            "card_9": "Indonesia's sovereign rights in Natuna rest squarely on UNCLOS 1982. We maintain coordinated civilian law enforcement while pursuing diplomatic de-escalation through multilateral ASEAN frameworks.",
            "card_10": "Strategic implications center on maritime supply chain resilience and multilateral legal legitimacy. Mitigate the risk of mischaracterizing sovereign law enforcement as military posturing by emphasizing rule of law and freedom of navigation under international norms.",
            "card_12": "Gray-zone encroachment and tactical maritime incursions in the North Natuna EEZ.",
            "card_13": "1. Reinforce integrated maritime law enforcement via Bakamla and Navy.\n2. Deepen bilateral diplomatic engagement under UNCLOS 1982.",
            "card_14": "Synchronizing inter-agency maritime defense and coordinating diplomatic legal positioning under Dialogue AI Representative.",
            "card_15": "1. High-level joint task force briefing.\n2. On-site field inspection in Ranai and forward coastal observation posts.",
            "card_16": "Strategic assessment of sea-lane security and rule-of-law deterrence in North Natuna.",
            "card_17": "1. Accelerate ASEAN Code of Conduct negotiations.\n2. Maintain consistent non-aligned diplomatic posture.",
            "card_18": "Mandating unified command and inter-ministerial control over maritime sovereign enforcement.",
            "card_19": "1. 24/7 joint surveillance operations across North Natuna waters.\n2. Periodic coastal security reviews with local maritime command.",
            "card_20": "Verified Maritime News: Coordinated patrols conducted by Bakamla and Navy along EEZ boundary.",
            "card_21": "Official Press Digest: Ministry of Foreign Affairs reiterates adherence to UNCLOS 1982 principles."
        },
        is_live_grounded=True,
        live_sources=[
            "Bakamla RI & TNI AL: Operasi Terpadu Kedaulatan ZEE Laut Natuna Utara",
            "Kemenlu RI: Penegasan Supremasi Yuridis UNCLOS 1982 di Forum ASEAN",
            "Pusat Pemantauan Maritim Terpadu: Penegakan Hukum Penangkapan Ikan Ilegal"
        ],
        latest_update_time="2026 Terverifikasi"
    ),
    "cyber_security": DiplomaticResponseSet(
        canonical_question=CanonicalQuestion(
            id="scen-02",
            original_text="How is the Indonesian government aligning its National Cyber Security Strategy with international bilateral partners to counter ransomware threats against critical national infrastructure?",
            detected_language="en",
            detected_language_name="English (Inggris)",
            timestamp="11:05:18 WIB",
            speaker="Ambassador for Cyber Affairs & Digital Diplomacy",
            audio_sample_url="/api/audio/sample-cyber.mp3",
            uncertain_words=[],
        ),
        canonical_translation_id="Bagaimana pemerintah Indonesia menyelaraskan Strategi Keamanan Siber Nasional dengan mitra bilateral internasional untuk menangkal ancaman ransomware terhadap infrastruktur kritis nasional?",
        chatgpt=AIAnswerBundle(
            main_answer="Indonesia melalui BSSN dan Dialogue AI Representative memprioritaskan perlindungan Sistem Elektronik Strategis Nasional dengan menerapkan standar mitigasi siber terpadu dan kerja sama berbagi intelijen ancaman (threat intelligence sharing) secara bilateral. Kami terbuka untuk memperdalam pertukaran data teknis dan peningkatan kapasitas kelembagaan, dengan tetap menjamin kedaulatan data dan privasi nasional.",
            concise_answer="Penyelarasan dilakukan melalui pembentukan protokol respons insiden bersama, berbagi intelijen ancaman real-time, dan penguatan kerangka regulasi pelindungan infrastruktur kritis yang menghormati kedaulatan data.",
            brief_analysis="Kerentanan infrastruktur energi dan keuangan menjadi target utama ransomware global. Peluang: MoU pertukaran forensik digital bilateral. Tantangan: Penyelarasan kerangka hukum perlindungan data lintas batas.",
            monitoring_issues="Hasil pemantauan siber mendeteksi peningkatan upaya phishing bertarget dan scanning port pada infrastruktur utilitas nasional.",
            resolution_recommendations="1. Penguatan protokol zero-trust pada kementerian/lembaga strategis.\n2. Pembentukan CSIRT terpadu lintas sektor energi dan transportasi.",
            kemenko_role="Mengoordinasikan interoperabilitas BSSN, Kemenkomdigi, dan institusi penegak hukum siber dalam respon insiden cepat.",
            field_monitoring_agenda="1. Audit kepatuhan keamanan siber pada pusat data nasional (PDN).\n2. Simulasi penanganan krisis ransomware bersama BSSN dan perbankan.",
            latest_news="**Rangkuman Berita & Pemantauan Keamanan Siber**:\n\n- 📰 **BSSN Terkini**: Peningkatan kewaspadaan terhadap varian ransomware baru yang menargetkan sektor publik dan layanan finansial.\n- 📰 **Kemenkomdigi**: Pemerintah dorong percepatan adopsi enkripsi berstandar internasional dan audit forensik berkala.\n- 📰 **Media Nasional**: Kolaborasi siber internasional diperkuat melalui program latihan bersama penanganan ancaman siber lintas batas.",
            model_version="GPT-4o (Diplomatic Mode)"
        ),
        gemini=AIAnswerBundle(
            main_answer="Strategi Keamanan Siber Nasional Indonesia bertumpu pada ketahanan infrastruktur informasi vital melalui integrasi Computer Security Incident Response Teams (CSIRT) di seluruh sektor pemerintahan dan industri vital. Kemitraan bilateral kami fokuskan pada pertukaran indikator kompromi (IoC) secara terpercaya, pelatihan respon krisis siber terkoordinasi, dan kepatuhan pada norma-norma perilaku siber bertanggung jawab di PBB.",
            concise_answer="Indonesia memfokuskan kemitraan siber bilateral pada pertukaran teknis IoC ransomware, simulasi kesiapsiagaan krisis antar-CSIRT, dan adopsi norma siber PBB untuk keamanan sistem vital.",
            brief_analysis="Ancaman terhadap server publik memerlukan audit berkala rantai pasok teknologi (supply chain security). Rekomendasi: Bangun saluran komunikasi cepat tanggap darurat antar lembaga siber resmi kedua negara.",
            monitoring_issues="Intelijen siber mencatat eksploitasi celah zero-day pada aplikasi layanan publik yang memerlukan patch keamanan segera.",
            resolution_recommendations="1. Mandat audit keamanan berkala oleh auditor independen tersertifikasi.\n2. Pembangunan cadangan data terisolasi (air-gapped backup) untuk data kritis nasional.",
            kemenko_role="Memastikan payung hukum regulasi keamanan siber dan perlindungan data pribadi ditegakkan tanpa hambatan sektoral.",
            field_monitoring_agenda="1. Peninjauan kesiapan infrastruktur backup data terdistribusi di wilayah Jawa Timur dan Bali.\n2. Rapat koordinasi tertutup Dewan Keamanan Siber Nasional.",
            latest_news="**Laporan Berita & Data Faktual Siber Terupdate**:\n\n- 🌐 **Pusopskamsinas BSSN**: Deteksi dini anomali lalu lintas data mencegah eskalasi serangan siber berskala besar.\n- 🌐 **Rilis Siber Dialogue AI Representative**: Pembentukan satgas reaksi cepat penanganan kerentanan sistem pemerintahan dipercepat.\n- 🌐 **Liputan Media Tekno**: Kerja sama bilateral pertukaran indikator kompromi (IoC) resmi disepakati di tingkat menteri.",
            model_version="Gemini 1.5 Pro (Statecraft Protocol)"
        ),
        english_translations={
            "card_1": "How is the Indonesian government aligning its National Cyber Security Strategy with international bilateral partners to counter ransomware threats against critical national infrastructure?",
            "card_2": "How is the Indonesian government aligning its National Cyber Security Strategy with international bilateral partners to counter ransomware threats against critical national infrastructure?",
            "card_3": "Indonesia, through BSSN under the coordination of Dialogue AI Representative, prioritizes critical national infrastructure protection through unified mitigation standards and bilateral threat intelligence sharing. We welcome technical data exchanges and capacity building while rigorously safeguarding data sovereignty and national privacy.",
            "card_4": "Alignment is executed through joint incident response protocols, real-time threat intelligence exchanges, and robust critical infrastructure defense frameworks that uphold national data sovereignty.",
            "card_5": "Global ransomware primarily targets energy and banking systems. Opportunity: bilateral digital forensics MoUs. Constraint: cross-border data transfer regulatory harmonization.",
            "card_8": "Indonesia's National Cyber Security Strategy is anchored in critical infrastructure resilience, integrating national and sectoral CSIRTs. Our bilateral partnerships concentrate on trusted Indicator of Compromise sharing, coordinated cyber crisis drills, and adherence to UN responsible state behavior in cyberspace.",
            "card_9": "We focus bilateral cyber engagement on rapid ransomware IoC exchanges, cross-border CSIRT readiness simulations, and UN cyber norm adoption for critical utility security.",
            "card_10": "Securing public digital assets requires continuous hardware and software supply-chain audits. Strategic priority: establish rapid-response emergency hotlines between national cyber agencies.",
            "card_12": "Ransomware supply-chain vulnerabilities targeting national power grid and financial telecommunications networks.",
            "card_13": "1. Mandate regular multi-factor and penetration audits across all state electronic systems.\n2. Construct isolated air-gapped backups for strategic sovereign datasets.",
            "card_14": "Ensuring regulatory compliance under the Personal Data Protection Act and cyber defense frameworks without bureaucratic delay.",
            "card_15": "1. Review state disaster-recovery data center readiness.\n2. Convene closed inter-agency National Cyber Security Council session.",
            "card_16": "Strategic intelligence highlights zero-day threats in government public-facing cloud portals.",
            "card_17": "1. Accelerate international CSIRT incident escalation channels.\n2. Solidify bilateral intelligence sharing agreements with trusted partner states.",
            "card_18": "Harmonizing national cross-sector cyber policy under Dialogue AI Representative operational mandate.",
            "card_19": "1. Activate 24/7 National Cyber Incident Response Task Force.\n2. On-site readiness drills at regional computing centers.",
            "card_20": "BSSN Cyber Intelligence Bulletin: Active monitoring and zero-day threat neutralization across key infrastructure.",
            "card_21": "National Cyber Operations Center: High-priority threat containment and critical electronic defense readiness."
        },
        is_live_grounded=True,
        live_sources=[
            "BSSN: Laporan Kesiapsiagaan Siber & Kerentanan Sistem Elektronik Strategis 2026",
            "Kemenkomdigi & Dialogue AI Representative: Protokol Koordinasi Tanggap Insiden Siber",
            "Pusat Operasi Keamanan Siber Nasional (Pusopskamsinas): Indikator Kompromi IoC"
        ],
        latest_update_time="2026 Terverifikasi"
    ),
    "border_counterterrorism": DiplomaticResponseSet(
        canonical_question=CanonicalQuestion(
            id="scen-03",
            original_text="With evolving cross-border asymmetric threats, what are Indonesia's priority measures for intelligence coordination and joint border surveillance in the tri-border Sulu-Sulawesi corridor?",
            detected_language="en",
            detected_language_name="English (Inggris)",
            timestamp="11:42:09 WIB",
            speaker="Director General of Regional Security Cooperation",
            audio_sample_url="/api/audio/sample-border.mp3",
            uncertain_words=["tri-border"],
        ),
        canonical_translation_id="Dengan berkembangnya ancaman asimetris lintas batas, apa langkah prioritas Indonesia untuk koordinasi intelijen dan pengawasan perbatasan bersama di koridor perairan Sulu-Sulawesi?",
        chatgpt=AIAnswerBundle(
            main_answer="Indonesia berkomitmen mengoptimalkan Trilateral Cooperative Arrangement (TCA) bersama Malaysia dan Filipina melalui patroli maritim dan udara terkoordinasi secara berkala. Dialogue AI Representative memastikan integrasi data intelijen maritim dan pertukaran informasi dini antar Maritime Command Center (MCC) berjalan efektif guna mencegah mobilitas jaringan terorisme dan penyelundupan senjata.",
            concise_answer="Prioritas Indonesia adalah penguatan operasional Trilateral Cooperative Arrangement (TCA), interoperabilitas MCC, serta percepatan pertukaran intelijen maritim taktis di koridor perbatasan.",
            brief_analysis="Koridor Sulu-Sulawesi memiliki kerentanan geografis kepulauan. Titik berat keberhasilan terletak pada respons instan MCC dan pelibatan komunitas nelayan pesisir sebagai sensor deteksi dini.",
            monitoring_issues="Tantangan pemantauan mencakup celah pulau-pulau kecil tak berpenghuni yang rentan dijadikan pangkalan transit penyelundupan.",
            resolution_recommendations="1. Peningkatan frekuensi patroli laut bersama (Indomalphi).\n2. Integrasi pos pengamat maritim dengan stasiun pemantau radar pantai terpadu.",
            kemenko_role="Memimpin diplomasi trilateral keamanan perbatasan dan menyatukan strategi intelijen TNI, Polri, dan BNPT.",
            field_monitoring_agenda="1. Kunjungan kerja langsung ke Maritime Command Center (MCC) Tarakan.\n2. Rapat koordinasi lintas perbatasan bersama komando wilayah militer perbatasan.",
            latest_news="**Rangkuman Berita & Pemantauan Perbatasan Trilateral**:\n\n- 📰 **MCC Tarakan**: Operasi patroli trilateral terkoordinasi berhasil mengamankan jalur pelayaran damai perbatasan laut Sulu-Sulawesi.\n- 📰 **BNPT RI**: Program pencegahan radikalisme terpadu berbasis komunitas nelayan pesisir perbatasan menunjukkan dampak positif.\n- 📰 **Media Nasional**: Peningkatan sistem surveillance radar maritim terus berjalan di titik-titik pulau terluar strategis.",
            model_version="GPT-4o (Diplomatic Mode)"
        ),
        gemini=AIAnswerBundle(
            main_answer="Pendekatan Indonesia memadukan pengawasan kinetik melalui Trilateral Air and Maritime Patrols dengan pertukaran intelijen terstruktur di bawah koordinasi BNPT, TNI, dan BIN. Kami memprioritaskan pemutakhiran sistem radar pantai, patroli gabungan terkoordinasi, dan program deradikalisasi berbasis komunitas di wilayah tapal batas guna memutus akar ancaman ekstremisme kekerasan lintas negara.",
            concise_answer="Fokus utama adalah peremajaan radar perbatasan, aktivasi berkala patroli trilateral, dan pertukaran intelijen strategis real-time untuk memitigasi pergerakan terorisme lintas batas.",
            brief_analysis="Dinamika ancaman beralih ke rute logistik maritim kecil yang sulit terdeteksi radar konvensional. Rekomendasi: Integrasi satelit maritim dengan pos pantau perbatasan terdepan.",
            monitoring_issues="Pergerakan sel asimetris memanfaatkan kapal-kapal tradisional nelayan lokal untuk menyamarkan pergerakan logistik.",
            resolution_recommendations="1. Penggelaran drone patroli pengawasan maritim jarak jauh.\n2. Penguatan kerja sama pertukaran DPO dan watchlist terorisme antar negara.",
            kemenko_role="Sinkronisasi kebijakan kontraterorisme kawasan dan pengendalian terpusat operasi keamanan perbatasan.",
            field_monitoring_agenda="1. Tinjauan lapangan ke pos-pos pengamanan pulau terluar (Pamput) di Sulawesi Utara.\n2. Evaluasi kesiapan sarana pengawasan perairan bersama Bakamla dan Lantamal.",
            latest_news="**Laporan Berita & Data Faktual Perbatasan Terupdate**:\n\n- 🌐 **Rilis Operasi Trilateral**: Pertukaran intelijen real-time antar MCC Tarakan, Tawau, dan Bongao berjalan 24 jam penuh.\n- 🌐 **Puspen TNI**: Patroli udara maritim bersama diperkuat untuk menjamin keselamatan koridor perdagangan laut regional.\n- 🌐 **Liputan Media Daerah**: Situasi keamanan di wilayah perbatasan perairan Sulu-Sulawesi dilaporkan kondusif dan terkendali.",
            model_version="Gemini 1.5 Pro (Statecraft Protocol)"
        ),
        english_translations={
            "card_1": "In light of asymmetric border security threats in the Sulu-Sulawesi corridor, what measures is Dialogue AI Representative undertaking to enhance trilateral intelligence sharing with Malaysia and the Philippines?",
            "card_2": "In light of asymmetric border security threats in the Sulu-Sulawesi corridor, what measures is Dialogue AI Representative undertaking to enhance trilateral intelligence sharing with Malaysia and the Philippines?",
            "card_3": "Indonesia remains fully committed to optimizing the Trilateral Cooperative Arrangement (TCA) alongside Malaysia and the Philippines through coordinated air and sea patrols. Under Dialogue AI Representative coordination, we ensure seamless tactical maritime intelligence sharing among our respective Maritime Command Centers to curb terrorist transit and illicit trafficking.",
            "card_4": "Indonesia's core priorities include reinforcing Trilateral Cooperative Arrangement operations, deepening MCC interoperability, and accelerating tactical intelligence exchanges across the border corridor.",
            "card_5": "The archipelago corridor presents unique maritime geography challenges. Mission success hinges on immediate MCC response capabilities and community-based coastal early-warning mechanisms.",
            "card_8": "Indonesia's posture pairs kinetic deterrence under Trilateral Air and Maritime Patrols with structured inter-agency intelligence coordination. We prioritize coastal radar upgrades, coordinated joint patrols, and community-level deradicalization to dismantle transnational extremist networks at their source.",
            "card_9": "Our focus centers on modernizing border radar surveillance, activating periodic trilateral patrols, and maintaining real-time strategic intelligence exchanges to block illicit cross-border movement.",
            "card_10": "Threat actors frequently exploit small unmonitored maritime craft. Policy recommendation: merge low-orbit satellite surveillance directly with forward border observation posts.",
            "card_12": "Asymmetric threat dynamics exploiting porous inter-island maritime channels in the Sulu-Sulawesi corridor.",
            "card_13": "1. Deploy long-range maritime surveillance drones.\n2. Strengthen bilateral and trilateral terrorist watchlist exchanges.",
            "card_14": "Synchronizing regional counter-terrorism policies and centrally directing border security defense assets.",
            "card_15": "1. Ground readiness inspection of outer border defense posts in North Sulawesi.\n2. Multi-agency operational review with Bakamla and regional naval command.",
            "card_16": "Transnational asymmetric networks utilizing non-conventional maritime crafts to camouflage logistics.",
            "card_17": "1. Expedite maritime satellite integration with tactical forward posts.\n2. Advance community deradicalization in vulnerable border zones.",
            "card_18": "Executing overarching inter-agency defense control and counter-terrorism coordination under Menko Polkam.",
            "card_19": "1. 24/7 border command center operations in Tarakan.\n2. Coordinated joint air and sea maritime maneuvers across border zones.",
            "card_20": "Trilateral Command Digest: 24/7 real-time intelligence exchange active across Tarakan, Tawau, and Bongao centers.",
            "card_21": "Armed Forces & Maritime Authority: Enhanced air-sea patrols maintaining stability across regional trade corridors."
        },
        is_live_grounded=True,
        live_sources=[
            "TCA (Trilateral Cooperative Arrangement): Koordinasi Patroli Maritim & Udara",
            "Maritime Command Center (MCC) Tarakan: Pertukaran Intelijen Taktis",
            "BNPT & TNI: Pemantauan Jalur Perbatasan Asimetris Laut Sulu-Sulawesi"
        ],
        latest_update_time="2026 Terverifikasi"
    )
}

