"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import toast from "react-hot-toast";
import { Gift, Copy, Check, ChevronDown } from "lucide-react";
import { weddingConfig } from "@/lib/wedding-config";
import { Section, SectionLabel, SectionTitle } from "@/components/ui/Section";
import { BotanicalDivider } from "@/components/ui/Ornaments";
import { copyToClipboard } from "@/lib/utils";

export function DigitalGift() {
  const [expanded, setExpanded] = useState(false);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  if (!weddingConfig.gifts.enabled) return null;

  const handleCopy = async (key: string, value: string) => {
    const ok = await copyToClipboard(value);
    if (ok) {
      setCopiedKey(key);
      toast.success("Nomor disalin");
      setTimeout(() => setCopiedKey(null), 2000);
    } else {
      toast.error("Gagal menyalin");
    }
  };

  return (
    <Section id="gift">
      <SectionLabel>Wedding Gift</SectionLabel>
      <SectionTitle>Amplop Digital</SectionTitle>
      <BotanicalDivider className="mx-auto mt-4" />

      <p className="mx-auto mt-6 max-w-md text-center text-xs leading-relaxed text-forest/70">
        {weddingConfig.gifts.description}
      </p>

      <div className="mt-8 text-center">
        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          className="inline-flex items-center gap-2 rounded-full bg-forest px-6 py-3 text-xs font-semibold uppercase tracking-widest text-cream shadow-soft transition-all hover:bg-forest-700 active:scale-95"
        >
          <Gift className="h-3.5 w-3.5" />
          {expanded ? "Tutup" : "Kirim Hadiah"}
          <motion.span animate={{ rotate: expanded ? 180 : 0 }}>
            <ChevronDown className="h-3.5 w-3.5" />
          </motion.span>
        </button>
      </div>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.4 }}
            className="overflow-hidden"
          >
            <div className="mt-6 space-y-3">
              {weddingConfig.gifts.bankAccounts.map((acc, i) => {
                const key = `bank-${i}`;
                return (
                  <motion.div
                    key={key}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.3, delay: i * 0.05 }}
                    className="glass-panel p-5 shadow-soft"
                  >
                    <div className="flex items-center justify-between">
                      <p className="text-[10px] font-bold uppercase tracking-widest text-terracotta">
                        Bank {acc.bank}
                      </p>
                      <span className="rounded-full bg-sage-100 px-2 py-0.5 text-[9px] font-medium text-forest">
                        Transfer
                      </span>
                    </div>
                    <p className="mt-3 font-display text-2xl tracking-wider text-forest tabular-nums">
                      {acc.accountNumber}
                    </p>
                    <p className="mt-1 text-xs text-forest/70">
                      a.n. {acc.accountName}
                    </p>
                    <button
                      type="button"
                      onClick={() => handleCopy(key, acc.accountNumber)}
                      className="mt-3 inline-flex items-center gap-2 rounded-full border border-forest/20 bg-cream-light px-4 py-1.5 text-[11px] font-medium tracking-wider text-forest transition-all hover:border-forest/40 active:scale-95"
                    >
                      {copiedKey === key ? (
                        <>
                          <Check className="h-3 w-3 text-sage-600" />
                          Tersalin
                        </>
                      ) : (
                        <>
                          <Copy className="h-3 w-3" />
                          Salin Nomor
                        </>
                      )}
                    </button>
                  </motion.div>
                );
              })}

              {weddingConfig.gifts.eWallets.map((wallet, i) => {
                const key = `wallet-${i}`;
                return (
                  <motion.div
                    key={key}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{
                      duration: 0.3,
                      delay: (weddingConfig.gifts.bankAccounts.length + i) * 0.05,
                    }}
                    className="glass-panel p-5 shadow-soft"
                  >
                    <div className="flex items-center justify-between">
                      <p className="text-[10px] font-bold uppercase tracking-widest text-terracotta">
                        {wallet.name}
                      </p>
                      <span className="rounded-full bg-sand-100 px-2 py-0.5 text-[9px] font-medium text-forest">
                        E-Wallet
                      </span>
                    </div>
                    <p className="mt-3 font-display text-2xl tracking-wider text-forest tabular-nums">
                      {wallet.number}
                    </p>
                    <p className="mt-1 text-xs text-forest/70">
                      a.n. {wallet.accountName}
                    </p>
                    <button
                      type="button"
                      onClick={() => handleCopy(key, wallet.number)}
                      className="mt-3 inline-flex items-center gap-2 rounded-full border border-forest/20 bg-cream-light px-4 py-1.5 text-[11px] font-medium tracking-wider text-forest transition-all hover:border-forest/40 active:scale-95"
                    >
                      {copiedKey === key ? (
                        <>
                          <Check className="h-3 w-3 text-sage-600" />
                          Tersalin
                        </>
                      ) : (
                        <>
                          <Copy className="h-3 w-3" />
                          Salin Nomor
                        </>
                      )}
                    </button>
                  </motion.div>
                );
              })}
            </div>

            <p className="mt-6 px-4 text-center text-[11px] italic leading-relaxed text-forest/55">
              Mohon konfirmasi jumlah &amp; nama pengirim setelah transfer agar
              kami dapat mengucapkan terima kasih secara langsung.
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </Section>
  );
}
