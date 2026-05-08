/**
 * Central wedding configuration
 * ──────────────────────────────────────────────────────────────
 * All wedding-specific data lives here so non-developers can update
 * content without touching component code. Edit values, save, hot
 * reload picks it up.
 */

export const weddingConfig = {
  // ── Couple ────────────────────────────────────────────────
  groom: {
    fullName: "Andyka Eka Putra",
    nickname: "Andyka",
    fatherName: "Bapak [Nama Ayah Andyka]",
    motherName: "Ibu [Nama Ibu Andyka]",
    childOrder: "Putra dari", // "Putra pertama dari" etc
    instagram: "andyka",
    photo: "/images/groom.jpg", // placeholder for now
  },
  bride: {
    fullName: "Khusnul Maulida",
    nickname: "Khusnul",
    fatherName: "Bapak [Nama Ayah Khusnul]",
    motherName: "Ibu [Nama Ibu Khusnul]",
    childOrder: "Putri dari",
    instagram: "khusnul",
    photo: "/images/bride.jpg",
  },

  // ── Event date & time ─────────────────────────────────────
  // ISO format with timezone — used for countdown calculation
  weddingDate: "2026-06-14T08:00:00+08:00",

  events: [
    {
      id: "akad",
      label: "Akad Nikah",
      date: "2026-06-14",
      time: "08:00 - 10:00 WITA",
      venue: "Lokasi Akad (TBD)",
      address: "Alamat lengkap akan diisi nanti",
      mapsUrl: "https://maps.google.com",
      mapsEmbedUrl:
        "https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3945.7944!2d115.21274!3d-8.670458!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x2dd2400b75a06aef%3A0x9f81eafce18ab9e8!2sBali!5e0!3m2!1sen!2sid!4v1700000000000",
    },
    {
      id: "resepsi",
      label: "Resepsi",
      date: "2026-06-14",
      time: "18:00 - 22:00 WITA",
      venue: "Lokasi Resepsi (TBD)",
      address: "Alamat lengkap akan diisi nanti",
      mapsUrl: "https://maps.google.com",
      mapsEmbedUrl:
        "https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3945.7944!2d115.21274!3d-8.670458!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x2dd2400b75a06aef%3A0x9f81eafce18ab9e8!2sBali!5e0!3m2!1sen!2sid!4v1700000000000",
    },
  ],

  // ── Optional sacred verse / quote shown at top of invitation ──
  openingQuote: {
    text: "Dan di antara tanda-tanda kekuasaan-Nya ialah Dia menciptakan untukmu istri-istri dari jenismu sendiri, supaya kamu cenderung dan merasa tenteram kepadanya, dan dijadikan-Nya di antaramu rasa kasih dan sayang.",
    source: "QS. Ar-Rum: 21",
  },

  // ── Love story timeline ───────────────────────────────────
  loveStory: [
    {
      year: "2020",
      title: "Pertemuan Pertama",
      description: "Kami pertama kali bertemu di acara ...",
    },
    {
      year: "2022",
      title: "Resmi Berpacaran",
      description: "Memutuskan untuk menjalani hubungan yang serius.",
    },
    {
      year: "2025",
      title: "Lamaran",
      description: "Hari di mana kedua keluarga akhirnya bersatu.",
    },
    {
      year: "2026",
      title: "Hari Pernikahan",
      description: "Memulai babak baru sebagai sepasang suami istri.",
    },
  ],

  // ── Gallery (placeholder for now) ─────────────────────────
  gallery: [
    "/images/gallery/01.jpg",
    "/images/gallery/02.jpg",
    "/images/gallery/03.jpg",
    "/images/gallery/04.jpg",
    "/images/gallery/05.jpg",
    "/images/gallery/06.jpg",
  ],

  // ── Digital gift / amplop ─────────────────────────────────
  gifts: {
    enabled: true,
    description:
      "Doa restu Anda merupakan karunia yang sangat berarti bagi kami. Namun jika ingin memberikan tanda kasih, kami menerima dengan penuh rasa syukur.",
    bankAccounts: [
      {
        bank: "BCA",
        accountNumber: "1234567890",
        accountName: "Andyka Eka Putra",
        logo: "/images/banks/bca.png",
      },
      {
        bank: "Mandiri",
        accountNumber: "0987654321",
        accountName: "Khusnul Maulida",
        logo: "/images/banks/mandiri.png",
      },
    ],
    eWallets: [
      {
        name: "GoPay / OVO / DANA",
        number: "081234567890",
        accountName: "Andyka Eka Putra",
      },
    ],
  },

  // ── Background music ──────────────────────────────────────
  music: {
    enabled: true,
    src: "/audio/bg-music.mp3",
    title: "Wedding Theme",
    autoplayOnOpen: true,
  },

  // ── Site metadata ─────────────────────────────────────────
  meta: {
    title: "Andyka & Khusnul · 14 Juni 2026",
    description:
      "Dengan memohon rahmat dan ridho Allah SWT, kami mengundang Bapak/Ibu/Saudara/i untuk menghadiri acara pernikahan kami.",
    siteUrl: "https://undangan.gopokaja.com",
    ogImage: "/images/og-image.svg",
  },
} as const;

export type WeddingConfig = typeof weddingConfig;
