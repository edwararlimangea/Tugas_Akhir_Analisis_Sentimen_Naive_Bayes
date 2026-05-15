#spasi tidak di atur tadi nilanya tinggi
# utils/preprocessing.py
import re
import string
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory

# ── Kamus Slang ──────────────────────────────────────────────────────────
# Diperluas berdasarkan analisis komentar data bencana Sumatera
# PERBAIKAN: Hapus entri 1 huruf ambigu (g, w), hapus self-mapping (kata baku ke dirinya sendiri)
slang_dict = {
    # Tambahan kata slang/normalisasi kata
    "tdk"       : "tidak",
    "rkyt"      : "rakyat",
    "mmg"       : "memang",
    "hrganya"   : "harga",
    "gk"        : "tidak",
    "jdi"       : "jadi",
    "indo"      : "indonesia",
    "g"         : "tidak",
    "nkri"      : "negara kesatuan republik indonesia",
    "koar"      : "berteriak",
    "sumatra"   : "sumatera",
    "fikiran"   : "pikiran",
    "kbykan"    : "kebanyakan",
    "org"       : "orang",
    "sumpek"    : "stres",
    # === Kata Ganti & Sapaan ===
    "btw"       : "ngomong-ngomong",
    # "komentar2" : "komentar komentar",
    "supporter " :"dukung ",
    "prabs"     : "prabowo",
    "presden"   : "presiden",
    "gw"        : "saya",
    "ak"        : "saya",
    "gue"       : "saya",
    "gua"       : "saya",
    "gueh"      : "saya",
    "lu"        : "kamu",
    "loe"       : "kamu",
    "lo"        : "kamu",
    "mrk"       : "mereka",
    "sy"        : "saya",
    "km"        : "kamu",
    "kmu"       : "kamu",
    "ama"       : "dengan",
    "masi"      : "masih",
    "bener"     : "benar",
    "semngat"   : "semangat",
    "omon"      : "omong",
    "doang"     : "saja",
    "tlg"       : "tolong",
    "sgt"       : "sangat",
    "kemaren"   : "kemarin",
    "dapet"     : "dapat",
    "skrg"      : "sekarang",
    "brita"     : "berita",
    "itulh"     : "itu",
    "inilh"     : "ini",
    "dn"        : "dan",
    "n"         : "dan",
    "ttep"      : "tetap",
    "pk"        : "pak",
    # "milih": "dukung",
    # "memilih": "dukung",
    # "pilih": "dukung",

    # === Ekspresi / Interjeksi ===
    "anj"       : "anjing",
    "anis"      : "anies",
    "disalahinn": "disalahin",
    "cm"        : "cuman",
    "anjir"     : "anjing",
    "anjay"     : "wah",
    "anjg"      : "anjing",
    "ajg"       : "anjing",
    "anying"    : "anjing",
    "asw"       : "anjing",
    "jiir"      : "wah",
    "jirr"      : "wah",
    "bjir"      : "wah",
    "hadeh"     : "aduh",
    "wkwk"      : "haha",
    "wkwkwk"    : "haha",
    "wkwkks"    : "haha",
    "hahaha"    : "haha",
    "lol"       : "haha",
    "woy"       : "hei",
    "woi"       : "hei",
    "astaghfirullah" : "astaghfirullah",
    "alhamdulillah"  : "alhamdulillah",

    # === Kata Hubung & Partikel Informal ===
    "yg"        : "yang",
    "tpi"       : "tetapi",
    "tp"        : "tetapi",
    "krn"       : "karena",
    "karna"     : "karena",
    "krena"     : "karena",
    "kalo"      : "kalau",
    "klo"       : "kalau",
    "klau"      : "kalau",
    "kalu"      : "kalau",
    "kalok"     : "kalau",
    "kpd"       : "kepada",
    "dr"        : "dari",
    "dri"       : "dari",
    "drpd"      : "daripada",
    "dgn"       : "dengan",
    "dg"        : "dengan",
    "utk"       : "untuk",
    "buat"      : "untuk",
    "bwt"       : "untuk",
    "sbg"       : "sebagai",
    "spt"       : "seperti",
    "sblm"      : "sebelum",
    "stlh"      : "setelah",
    "sdgkn"     : "sedangkan",
    "sdngkn"    : "sedangkan",
    "wlpn"      : "walaupun",
    "pd"        : "pada",
    "sm"        : "dengan",
    "sma"       : "dengan",
    "spy"       : "supaya",

    # === Kata Kerja & Kata Sifat Informal ===
    "udah"      : "sudah",
    "udh"       : "sudah",
    "sdh"       : "sudah",
    "dah"       : "sudah",
    "blm"       : "belum",
    "jgn"       : "jangan",
    "emg"       : "memang",
    "emang"     : "memang",
    "hrs"       : "harus",
    "hrus"      : "harus",
    "bs"        : "bisa",
    "msh"       : "masih",
    "mo"        : "mau",
    "bakal"     : "akan",
    "bakalan"   : "akan",
    "nggak"     : "tidak",
    "ngk"       : "tidak",
    "ngga"      : "tidak",
    "gak"       : "tidak",
    "ga"        : "tidak",
    "engga"     : "tidak",
    "enggak"    : "tidak",
    "ndak"      : "tidak",
    "kagak"     : "tidak",
    "kaga"      : "tidak",
    "bkn"       : "bukan",
    "jd"        : "jadi",
    "jadiin"    : "jadikan",
    "bikin"     : "membuat",
    "bikinin"   : "membuatkan",
    "buatin"    : "membuatkan",
    "ngeliat"   : "melihat",
    "liat"      : "melihat",
    "liihat"    : "melihat",
    "ngerasain" : "merasakan",
    "ngerasakan": "merasakan",
    "ngetwit"   : "menulis",
    "ngetweet"  : "menulis",
    "ngetik"    : "menulis",
    "ngomong"   : "berbicara",
    "bilang"    : "berkata",
    "nulis"     : "menulis",
    "nyebut"    : "menyebut",
    "nunjukin"  : "menunjukkan",
    "diem"      : "diam",
    "selesain"  : "selesaikan",
    "urus"      : "mengurus",
    "ngurusin"  : "mengurus",
    "ngurus"    : "mengurus",
    "bantu"     : "membantu",
    "bantuin"   : "membantu",
    "kasih"     : "memberi",
    "dikasih"   : "diberikan",
    "kasi"      : "memberi",
    "gercep"    : "gerak cepat",
    "nonton"    : "menonton",
    "nyuruh"    : "menyuruh",
    "kepikiran" : "terpikirkan",
    "ngomongin" : "membicarakan",
    "ngebahas"  : "membahas",
    "ributin"   : "memperdebatkan",
    "nyalahin"  : "menyalahkan",
    "disalahin" : "disalahkan",
    "salahin"   : "menyalahkan",
    "ngijinin"  : "izinkan",
    "nutup"     : "tutup",
    "viralkan"  : "viral",

    # === Kata Benda / Topik Spesifik Konteks ===
    "wong"      : "orang",
    "bnyk"      : "banyak",
    "byk"       : "banyak",
    "pmrintah"  : "pemerintah",
    "bansos"    : "bantuan sosial",
    "huntara"   : "hunian sementara",
    "huntap"    : "hunian tetap",
    "bnpb"      : "badan nasional penanggulangan bencana",
    "mbg"       : "makan bergizi gratis",
    "sppg"      : "satuan pelayanan pemenuhan gizi",
    "klh"       : "kementerian lingkungan hidup",
    "kkp"       : "kementerian kelautan dan perikanan",
    "tni"       : "tentara nasional indonesia",
    "polri"     : "kepolisian republik indonesia",
    "sar"       : "search and rescue",
    "pu"        : "pekerjaan umum",
    "pln"       : "perusahaan listrik negara",
    "pmi"       : "palang merah indonesia",
    "dpr"       : "dewan perwakilan rakyat",
    "kpk"       : "komisi pemberantasan korupsi",
    # === Sentimen Negatif Informal ===
    "gapernah"  : "tidak pernah",
    "gaada"     : "tidak ada",
    "gakada"    : "tidak ada",
    "gasuka"    : "tidak suka",
    "gabisa"    : "tidak bisa",
    "gabakal"   : "tidak akan",
    "gamau"     : "tidak mau",
    "gaharus"   : "tidak harus",
    "gabisanya" : "tidak bisanya",
    "gaperlu"   : "tidak perlu",
    "gapunya"   : "tidak punya",
    "gapaham"   : "tidak paham",
    "gakpaham"  : "tidak paham",
    "gamasuk"   : "tidak masuk akal",
    "absurd"    : "tidak masuk akal",
    "gilak"     : "gila",
    "gokil"     : "luar biasa",
    "bgt"       : "banget",
    "segede"    : "sebesar",
    "keraas"    : "keras",
    "libgkungan": "lingkungan",
    "smoga"     : "semoga",
    "dzolim"    : "zalim",
    "tau"       : "tahu",
    "tauu"      : "tahu",
    "tauuu"     : "tahu",
    "tengelam"  : "tenggelam",
    "tanggung jawab" : "tanggung_jawab",
    "berduka cita"   : "duka_cita",
    "ngerti"        : "mengerti",

    # === TAMBAHAN SLANG TIKTOK / X (2023-2024) ===
    "ngegas"    : "marah",
    "gaskeun"   : "lakukan",
    "kesel"     : "kesal",
    "baper"     : "terbawa perasaan",
    "nyinyir"   : "mengkritik",
    "ghosting"  : "menghilang",
    "receh"     : "sepele",
    "lebay"     : "berlebihan",
    "sotoy"     : "sok tahu",
    "modus"     : "cara",
    "kepo"      : "ingin tahu",
    "bodo amat" : "tidak peduli",
    "gabut"     : "tidak ada kegiatan",
    "santuy"    : "santai",
    "ygy"       : "ya guys ya",
    "nolep"     : "tidak punya kehidupan sosial",
    "npwp"      : "numpang popularitas",
    "zonk"      : "gagal",
    "mager"     : "malas bergerak",
    "healing"   : "rehat",
    "relate"    : "relevan",
    "cringe"    : "memalukan",
    "toxic"     : "berbahaya",
    "plot twist": "kejutan",
    "exposure"  : "perhatian publik",
    "halu"      : "halusinasi",
    "bucin"     : "budak cinta",
    "nge-gas"   : "marah",
    "trigger"   : "memancing emosi",
    "red flag"  : "tanda bahaya",
    "green flag" : "tanda baik",
    "out of topic" : "keluar topik",
    "cancel"    : "memboikot",
    "clout"     : "popularitas",
    "drakor"    : "drama korea",
    "hits"      : "populer",
    "viral"     : "viral",
    "netizen"   : "warganet",
    "warganet"  : "warganet",
    "buzzer"    : "buzzer",
    "hoaks"     : "hoaks",
    "disinformasi": "disinformasi",
    "misinformasi": "misinformasi",

    # === Tambahan berdasarkan analisis misklasifikasi ===
    # Slang yang lolos dari filter sebelumnya (ditemukan di data error)
    "pdhl"        : "padahal",
    "jg"          : "juga",
    "juga"        : "juga",
    "yaudah"      : "sudahlah",
    "yaudahlah"   : "sudahlah",
    "ngotot"      : "keras kepala",
    "ngibul"      : "berbohong",
    "ngibulnya"   : "berbohongnya",
    "keitung"     : "terhitung",
    "waras"       : "waras",
    "moga"        : "semoga",
    "semoga"      : "semoga",
    "kagum"       : "kagum",
    "timba"       : "timba",
    "selubung"    : "selubung",
    "bebas"       : "bebas",
    "mamah"       : "ibu",
    "hut"         : "hutan",    # konteks "kayu hut" = kayu hutan
    "pdhl"        : "padahal",
    "tebang"      : "tebang",
    "liar"        : "liar",
}

# ── Stopwords ─────────────────────────────────────────────────────────────
# PERBAIKAN: Kata-kata sentimen penting TIDAK dimasukkan ke stopwords
# supaya konteks emosi dan evaluasi tidak hilang saat preprocessing.
# Kata yang SENGAJA TIDAK ada di sini (walaupun umum):
#   - "tidak", "bukan", "tak", "belum" → kata negasi, penting untuk sentimen
#   - "bagus", "baik", "buruk", "jelek" → kata evaluatif langsung
#   - "senang", "sedih", "marah", "kecewa" → kata emosi
#   - "bantu", "peduli", "aman", "selamat" → kata positif konteks bencana
#   - "lambat", "parah", "gagal", "rusak"  → kata negatif konteks bencana
stopwords = {
    # Kata umum (function words) — aman dihapus, tidak bermakna sentimen
    "dan", "yang", "di", "ke", "dengan", "atau", "juga",
    "pada", "itu", "ini", "dari", "dalam",
    "adalah", "oleh", "ada", "ko", "ya",

    # Partikel & filler — tidak bermakna
    "ya", "oh", "eh", "iya", "ok", "oke",
    "lah", "deh", "sih", "dong", "kok", "kan", "pun",
    "nya", "ter", "nah", "mah", "atuh", "toh", "ih",

    # Kata lokasi umum — tidak bermakna sentimen
    "sini", "sana", "situ", "kemari",

    # Kata netral umum
    "hal", "cara", "milik", "tempat",

    # Kata penghubung netral
    "seperti", "hingga", "sampai", "serta",
    "bahwa", "terhadap", "mengenai", "tentang",
    "para", "pihak", "bersama",
    "tersebut",

    # Sapaan
    "bapak", "pak", "ibu", "bu", "mas", "mbak", "kak",
    "bang", "abang", "adik", "kakak",

    # Sosial media
    "rt", "retweet", "via", "amp", "d",

    # Kata frekuensi tinggi tapi tidak bermakna sentimen
    # CATATAN: "juga" dan "sudah" TIDAK dimasukkan karena kadang
    # bermakna kontekstual. Hanya intensifier murni yang aman dihapus.
    "akan", "agar", "supaya",
    "lebih", "sekali", "paling",
    # "sangat" juga dikeluarkan dari sini — bisa memperkuat sentimen
    # contoh: "sangat kecewa", "sangat bagus"
}

# ── Kata Sentimen yang Wajib Dipertahankan (whitelist) ────────────────────
# Kata-kata ini TIDAK boleh dihapus meskipun muncul sebagai stopwords.
# Digunakan di fungsi remove_stopwords() untuk proteksi ekstra.
SENTIMENT_WHITELIST = {
    # Sentimen positif
    "bagus", "baik", "benar", "bersih", "berhasil", "cepat",
    "sigap", "tanggap", "peduli", "aman", "selamat", "setuju",
    "bangga", "senang", "puas", "mantap", "luar biasa", "hebat",
    "tepat", "adil", "merata", "terbuka", "transparan",
    "solidaritas", "empati", "simpati", "bantu",
    # Sentimen negatif
    "buruk", "jelek", "lambat", "gagal", "rusak", "parah",
    "kecewa", "marah", "kesal", "sedih", "menderita", "sengsara",
    "terlambat", "terabaikan", "diabaikan", "korupsi", "pungli",
    "zalim", "aniaya", "diskriminasi", "prihatin",
    "tidak_bagus", "tidak_baik", "tidak_cepat", "tidak_peduli",
    "tidak_ada", "tidak_serius", "tidak_adil", "tidak_mampu",
    "tidak_tanggap", "tidak_sigap", "tidak_berhasil",
    "tidak_merata", "tidak_cukup", "tidak_punya",
    # Kata evaluatif netral yang kontekstual
    "kritis", "gawat", "darurat", "mendesak", "serius",
    "hancur", "tenggelam", "tewas", "korban", "luka",
    # Tambahan dari analisis misklasifikasi
    "kagum", "waras", "bebas", "liar", "ngotot",
    "ngibul", "ngibulnya", "sarkasme", "sindir",
    "keras kepala", "berbohong", "berbohongnya",
    "tebang", "selubung", "moga", "semoga",
    "tidak_mau", "tidak_pakai", "tidak_ya", "tidak_memahami",
    "tidak_punya",
}

# Inisialisasi stemmer Sastrawi
factory = StemmerFactory()
stemmer = factory.create_stemmer()

# ── Custom Stem ───────────────────────────────────────────────────────────
# Kata yang tidak perlu di-stem atau perlu normalisasi khusus
# PERBAIKAN: Ditambah banyak kata domain bencana agar tidak salah stem
custom_stem = {
    # === Domain Bencana (kata inti — lindungi dari stemmer) ===
    "pemimpin"      : "pemimpin",
    "bencana"       : "bencana",
    "banjir"        : "banjir",
    "longsor"       : "longsor",
    "gempa"         : "gempa",
    "tsunami"       : "tsunami",
    "kebakaran"     : "kebakaran",
    "kekeringan"    : "kekeringan",
    "angin"         : "angin",
    "puting"        : "puting",
    "beliung"       : "beliung",
    "abrasi"        : "abrasi",
    "erupsi"        : "erupsi",
    "vulkanik"      : "vulkanik",
    "darurat"       : "darurat",
    "evakuasi"      : "evakuasi",
    "dievakuasi"    : "evakuasi",
    "pengungsian"   : "pengungsian",
    "pengungsi"     : "pengungsi",
    "diungsikan"    : "ungsikan",
    "terdampak"     : "terdampak",
    "korban"        : "korban",
    "penyintas"     : "penyintas",
    "meninggal"     : "meninggal",
    "tewas"         : "meninggal",
    "wafat"         : "meninggal",
    "hilang"        : "hilang",
    "luka"          : "luka",
    "terluka"       : "terluka",
    "selamat"       : "selamat",
    "diselamatkan"  : "selamat",
    "terlantar"     : "terlantar",
    "terisolasi"    : "terisolasi",
    "terisolir"     : "terisolasi",    # normalisasi
    "tenggelam"     : "tenggelam",
    "hancur"        : "hancur",
    "rusak"         : "rusak",
    "terputus"      : "terputus",
    "kelaparan"     : "kelaparan",
    "keracunan"     : "keracunan",
    "menderita"     : "menderita",
    "sengsara"      : "sengsara",

    # === Respons Bencana ===
    "bantuan"       : "bantuan",
    "bansos"        : "bantuan sosial",
    "donasi"        : "donasi",
    "relawan"       : "relawan",
    "penanganan"    : "penanganan",
    "penanggulangan": "penanggulangan",
    "pemulihan"     : "pemulihan",
    "rehabilitasi"  : "rehabilitasi",
    "rekonstruksi"  : "rekonstruksi",
    "huntara"       : "hunian sementara",
    "huntap"        : "hunian tetap",
    "tanggap"       : "tanggap",
    "tanggap darurat": "tanggap darurat",
    "sigap"         : "sigap",
    "evakuasi"      : "evakuasi",
    "logistik"      : "logistik",
    "distribusi"    : "distribusi",
    "koordinasi"    : "koordinasi",
    "mitigasi"      : "mitigasi",

    # === Evaluasi Respons (sentimen terhadap pemerintah/lembaga) ===
    "lambat"        : "lambat",
    "lambatnya"     : "lambat",        # normalisasi
    "keterlambatan" : "lambat",        # normalisasi ke root
    "cepat"         : "cepat",
    "cepatnya"      : "cepat",
    "sigap"         : "sigap",
    "gagal"         : "gagal",
    "kegagalan"     : "gagal",         # normalisasi
    "berhasil"      : "berhasil",
    "keberhasilan"  : "berhasil",
    "peduli"        : "peduli",
    "kepedulian"    : "peduli",        # normalisasi
    "tidak_peduli"  : "tidak_peduli",
    "ketidakpedulian": "tidak_peduli", # normalisasi
    "diabaikan"     : "diabaikan",
    "terabaikan"    : "diabaikan",     # normalisasi
    "terbengkalai"  : "terbengkalai",
    "prihatin"      : "prihatin",
    "kritis"        : "kritis",
    "gawat"         : "gawat",
    "parah"         : "parah",
    "serius"        : "serius",
    "darurat"       : "darurat",
    "mendesak"      : "mendesak",

    # === Institusi & Aktor ===
    "pemerintah"    : "pemerintah",
    "presiden"      : "presiden",
    "menteri"       : "menteri",
    "mentri"        : "menteri",       # normalisasi typo
    "pejabat"       : "pejabat",
    "bupati"        : "bupati",
    "gubernur"      : "gubernur",
    "walikota"      : "walikota",
    "bnpb"          : "badan nasional penanggulangan bencana",
    "basarnas"      : "basarnas",
    "korupsi"       : "korupsi",
    "pungli"        : "pungli",
    "anggaran"      : "anggaran",
    "dana"          : "dana",

    # === Lingkungan & Penyebab ===
    "sumatera"      : "sumatera",
    "nasional"      : "nasional",
    "sawit"         : "sawit",
    "hutan"         : "hutan",
    "deforestasi"   : "deforestasi",
    "lingkungan"    : "lingkungan",
    "ekologi"       : "ekologi",
    "tambang"       : "tambang",
    "pertambangan"  : "tambang",       # normalisasi
    "infrastruktur" : "infrastruktur",
    "drainase"      : "drainase",
    "daerah aliran sungai": "daerah aliran sungai",
    "das"           : "daerah aliran sungai",

    # === Sentimen Khusus ===
    "solidaritas"   : "solidaritas",
    "empati"        : "empati",
    "simpati"       : "simpati",
    "duka"          : "duka",
    "duka_cita"     : "duka_cita",
    "bela sungkawa" : "bela sungkawa",
    "kemanusiaan"   : "kemanusiaan",
    "keadilan"      : "keadilan",
    "ketidakadilan" : "tidak_adil",    # normalisasi
    "zalim"         : "zalim",
    "dzolim"        : "zalim",         # normalisasi
    "aniaya"        : "aniaya",
    "diskriminasi"  : "diskriminasi",

    # === Kata Kunci Media Sosial ===
    "buzzer"        : "buzzer",
    "hoaks"         : "hoaks",
    "disinformasi"  : "disinformasi",
    "misinformasi"  : "misinformasi",
    "pencitraan"    : "pencitraan",
    "framing"       : "framing",
    "provokasi"     : "provokasi",
    "propaganda"    : "propaganda",
    "narasi"        : "narasi",
    "viral"         : "viral",
    "trending"      : "trending",
    "warganet"      : "warganet",
    "netizen"       : "warganet",      # normalisasi

    # === Negasi gabungan dari kasus error ===
    "tidak_mau"       : "tidak_mau",
    "tidak_pakai"     : "tidak_pakai",
    "tidak_ya"        : "tidak_ya",
    "tidak_memahami"  : "tidak_memahami",
    "tidak_punya"     : "tidak_punya",
    "tidak_waras"     : "tidak_waras",
    "tidak_bebas"     : "tidak_bebas",

    # === Custom negasi gabungan ===
    "tidak_bagus"   : "tidak_bagus",
    "tidak_baik"    : "tidak_baik",
    "tidak_cepat"   : "tidak_cepat",
    "tidak_peduli"  : "tidak_peduli",
    "tidak_ada"     : "tidak_ada",
    "tidak_serius"  : "tidak_serius",
    "tidak_adil"    : "tidak_adil",
    "tidak_mampu"   : "tidak_mampu",
    "tidak_tanggap" : "tidak_tanggap",
    "tidak_sigap"   : "tidak_sigap",
    "tidak_berhasil": "tidak_berhasil",
    "tidak_merata"  : "tidak_merata",
    "tidak_cukup"   : "tidak_cukup",

    # === Lain-lain ===
    "setuju"        : "setuju",
    "sekedar"       : "sekedar",
    "tidak"         : "tidak",
    "bukan"         : "bukan",
    "ijin"          : "izin",
    "izin"          : "izin",
    "sembuh"        : "sembuh",
    "tanggung_jawab": "tanggung_jawab",
}

# ══════════════════════════════════════════════════════════════════════════
# TAHAPAN PREPROCESSING
# ══════════════════════════════════════════════════════════════════════════

def lowercase(text: str) -> str:
    return text.lower()

def remove_mention_url(text: str) -> str:
    text = re.sub(r'http\S+|www\.\S+', '', text)
    text = re.sub(r'@\w+', '', text)
    text = re.sub(r'#\w+', '', text)
    text = re.sub(r'\d+', '', text)
    
    # PERBAIKAN: Ganti tanda baca dengan spasi, bukan dihapus
    punct = string.punctuation.replace('_', '')
    text = re.sub(r'[' + re.escape(punct) + r']+', ' ', text)
    
    # Hapus karakter non-alfabetik/latin (pertahankan spasi)
    text = re.sub(r'[^\x00-\x7F\u00C0-\u024F\u1E00-\u1EFF\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def normalize_slang_text(text: str) -> str:
    # Ganti frasa multi-kata terlebih dahulu (prioritas lebih tinggi)
    sorted_slang = sorted(slang_dict.keys(), key=lambda x: len(x.split()), reverse=True)
    for slang in sorted_slang:
        if ' ' in slang:
            text = re.sub(r'\b' + re.escape(slang) + r'\b', slang_dict[slang], text)
    # Ganti per kata (hanya whole-word match)
    tokens = text.split()
    normalized = [slang_dict.get(w, w) for w in tokens]
    return ' '.join(normalized)

def negation_handling_text(text: str) -> str:
    """
    Gabungkan kata negasi dengan kata berikutnya menjadi token tunggal.
    Contoh: "tidak ada" → "tidak_ada", "bukan benar" → "tidak_benar"
    
    PERBAIKAN v2:
    - Skip partikel filler (ya, sih, kok, lah, dong) setelah negasi
      supaya "tidak ya bisa" → "tidak_bisa" bukan "tidak_ya"
    - Normalisasi semua negasi ke prefix "tidak_" agar konsisten di TF-IDF
    """
    negation_words = {
        "tidak", "bukan", "tak", "jangan", "belum", "tanpa", "tiada", "nihil",
    }
    # Partikel filler yang bisa muncul di antara negasi dan kata isinya
    filler_particles = {"ya", "sih", "kok", "lah", "dong", "deh", "pun", "kah"}
    
    tokens = text.split()
    result = []
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token in negation_words:
            # Cari kata isi berikutnya — lewati filler particle
            j = i + 1
            while j < len(tokens) and tokens[j] in filler_particles:
                j += 1
            
            if j < len(tokens) and tokens[j] not in negation_words:
                # Gabungkan negasi + kata isi
                result.append("tidak_" + tokens[j])
                # Lewati semua token yang sudah dikonsumsi (filler + kata isi)
                i = j + 1
                continue
            else:
                # Tidak ada kata isi valid — simpan negasi apa adanya
                result.append(token)
        else:
            result.append(token)
        i += 1
    return ' '.join(result)

def tokenize(text: str) -> list:
    return text.split()

def remove_stopwords(tokens: list) -> list:
    """
    Hapus stopwords dengan dua pengecualian:
    1. Token yang mengandung '_' (negasi gabungan: tidak_peduli, tidak_mampu, dll.)
    2. Token yang ada di SENTIMENT_WHITELIST (kata sentimen penting)
    """
    result = []
    for word in tokens:
        if '_' in word:
            result.append(word)
        elif word in SENTIMENT_WHITELIST:
            result.append(word)
        elif word in stopwords:
            continue
        else:
            result.append(word)
    return result

def safe_stem(word: str) -> str:
    if word in custom_stem:
        return custom_stem[word]
    if '_' in word:
        return word  # Jangan stem token negasi gabungan
    try:
        return stemmer.stem(word)
    except Exception:
        return word

def stemming(tokens: list) -> list:
    return [safe_stem(t) for t in tokens if t.strip()]

def preprocess_pipeline(text) -> list:
    """
    Pipeline preprocessing lengkap:
    1. Lowercase
    2. Hapus mention, URL, hashtag, angka, tanda baca
    3. Normalisasi slang (frasa dulu, lalu per kata)
    4. Penanganan negasi (gabungkan "tidak" + kata berikutnya)
    5. Tokenisasi
    6. Hapus stopwords (pertahankan token negasi gabungan)
    7. Stemming (dengan perlindungan custom_stem)
    """
    text = str(text)
    text = lowercase(text)
    text = remove_mention_url(text)
    text = normalize_slang_text(text)
    text = negation_handling_text(text)
    tokens = tokenize(text)
    tokens = remove_stopwords(tokens)
    tokens = stemming(tokens)
    return tokens

# ── Alias backward compatibility ─────────────────────────────────────────
def case_folding(text: str) -> str:
    return lowercase(text)

def cleaning(text: str) -> str:
    return remove_mention_url(text)

def normalize_slang(tokens: list) -> list:
    return [slang_dict.get(w, w) for w in tokens if slang_dict.get(w, w).strip()]

def negation_handling(tokens: list) -> list:
    negation_words = {
        "tidak", "bukan", "tak", "jangan", "belum", "tanpa", "tiada", "nihil",
    }
    result = []
    skip_next = False
    for i, token in enumerate(tokens):
        if skip_next:
            skip_next = False
            continue
        next_token = tokens[i + 1] if i + 1 < len(tokens) else None
        if token in negation_words and next_token and next_token not in negation_words:
            result.append("tidak_" + next_token)
            skip_next = True
        else:
            result.append(token)
    return result