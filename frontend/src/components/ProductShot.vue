<template>
  <div class="shot">
    <svg viewBox="0 0 200 200" aria-hidden="true">
      <rect width="200" height="200" fill="#f6f6f6" />
      <g v-if="kind === 'phone'">
        <rect x="68" y="28" width="64" height="144" rx="12" :fill="body" />
        <rect x="74" y="40" width="52" height="108" rx="4" fill="#d9ecff" />
        <circle cx="100" cy="158" r="4" fill="#fff" opacity="0.7" />
      </g>
      <g v-else-if="kind === 'fridge'">
        <rect x="58" y="24" width="84" height="152" rx="6" fill="#e8eef2" stroke="#c5d0d8" />
        <line x1="100" y1="24" x2="100" y2="176" stroke="#c5d0d8" />
        <rect x="90" y="70" width="4" height="22" rx="2" fill="#8aa0ad" />
        <rect x="106" y="70" width="4" height="22" rx="2" fill="#8aa0ad" />
      </g>
      <g v-else-if="kind === 'washer'">
        <rect x="46" y="36" width="108" height="128" rx="8" fill="#f3f4f6" stroke="#d0d5dd" />
        <circle cx="100" cy="108" r="36" fill="#dbe7f3" stroke="#9bb0c4" />
        <circle cx="100" cy="108" r="18" fill="#8fb4d6" />
        <rect x="62" y="50" width="28" height="8" rx="2" fill="#c5ced6" />
      </g>
      <g v-else-if="kind === 'ac'">
        <rect x="36" y="58" width="128" height="42" rx="6" fill="#f7f8fa" stroke="#d0d5dd" />
        <rect x="48" y="78" width="104" height="8" rx="2" fill="#b7c3ce" />
        <path d="M70 110 q10 18 0 28 M100 110 q10 18 0 28 M130 110 q10 18 0 28" fill="none" stroke="#9ad0f5" stroke-width="3" />
      </g>
      <g v-else-if="kind === 'microwave'">
        <rect x="40" y="54" width="120" height="84" rx="6" fill="#eceff3" stroke="#c5ced6" />
        <rect x="52" y="66" width="68" height="52" rx="3" fill="#c9d7e6" />
        <circle cx="140" cy="82" r="6" fill="#9aa8b5" />
        <rect x="134" y="96" width="12" height="18" rx="2" fill="#b7c3ce" />
      </g>
      <g v-else-if="kind === 'tv'">
        <rect x="32" y="48" width="136" height="86" rx="6" fill="#243044" />
        <rect x="40" y="56" width="120" height="70" fill="#3d7ea6" />
        <rect x="90" y="136" width="20" height="12" fill="#c5ced6" />
        <rect x="70" y="148" width="60" height="6" rx="2" fill="#9aa8b5" />
      </g>
      <g v-else-if="kind === 'soy'">
        <rect x="78" y="108" width="44" height="36" rx="4" fill="#d9dde3" />
        <path d="M86 108 L100 64 L114 108 Z" fill="#f4f6f8" stroke="#c5ced6" />
        <rect x="94" y="144" width="12" height="16" fill="#b7c3ce" />
      </g>
      <g v-else-if="kind === 'fan'">
        <circle cx="100" cy="78" r="36" fill="none" stroke="#9aa8b5" stroke-width="4" />
        <path d="M100 78 L100 46 M100 78 L128 96 M100 78 L72 96" stroke="#7f8c99" stroke-width="6" stroke-linecap="round" />
        <rect x="96" y="114" width="8" height="36" fill="#c5ced6" />
        <rect x="78" y="148" width="44" height="8" rx="3" fill="#9aa8b5" />
      </g>
      <g v-else-if="kind === 'heater'">
        <rect x="70" y="36" width="60" height="128" rx="30" fill="#f3f4f6" stroke="#c5ced6" />
        <rect x="82" y="58" width="36" height="16" rx="3" fill="#d0d5dd" />
        <circle cx="100" cy="120" r="8" fill="#e4572e" />
      </g>
      <g v-else-if="kind === 'hoodie'">
        <path d="M70 78 L86 62 H114 L130 78 L142 150 H58 Z" fill="#3d4c5c" />
        <path d="M86 62 Q100 86 114 62" fill="#2c3844" />
      </g>
      <g v-else-if="kind === 'jeans'">
        <path d="M72 48 H128 L122 156 H108 L100 96 L92 156 H78 Z" fill="#3d5f8a" />
        <path d="M86 48 H114 L110 64 H90 Z" fill="#314e72" />
      </g>
      <g v-else-if="kind === 'coat'">
        <path d="M64 70 L84 52 H116 L136 70 L128 156 H72 Z" fill="#7f1d1d" />
        <path d="M92 52 L100 78 L108 52" fill="#5c1212" />
      </g>
      <g v-else-if="kind === 'shirt'">
        <path d="M62 70 L82 54 H118 L138 70 L128 86 L116 74 V150 H84 V74 L72 86 Z" fill="#f4f7fb" stroke="#d0d5dd" />
      </g>
      <g v-else-if="kind === 'shoes'">
        <ellipse cx="78" cy="128" rx="34" ry="16" fill="#f2f2f2" stroke="#c5ced6" />
        <ellipse cx="124" cy="120" rx="34" ry="16" fill="#e8e8e8" stroke="#c5ced6" />
        <path d="M52 124 Q70 100 100 112" fill="none" stroke="#d4380d" stroke-width="3" />
      </g>
      <g v-else-if="kind === 'bag'">
        <rect x="62" y="64" width="76" height="88" rx="10" fill="#3f6212" />
        <path d="M78 64 V52 Q100 36 122 52 V64" fill="none" stroke="#3f6212" stroke-width="6" />
        <rect x="90" y="96" width="20" height="14" rx="3" fill="#d9f99d" />
      </g>
      <g v-else-if="kind === 'scarf'">
        <path d="M48 70 Q100 40 152 78 Q120 96 96 88 Q70 120 58 150" fill="none" stroke="#b91c1c" stroke-width="16" stroke-linecap="round" />
      </g>
      <g v-else-if="kind === 'pants'">
        <path d="M74 48 H126 L120 156 H104 L100 100 L96 156 H80 Z" fill="#4b5563" />
      </g>
      <g v-else-if="kind === 'milk'">
        <path d="M74 70 H126 L118 160 H82 Z" fill="#f8fafc" stroke="#d0d5dd" />
        <path d="M86 70 V52 H114 V70" fill="#e2e8f0" />
        <rect x="86" y="96" width="28" height="28" fill="#16a34a" />
      </g>
      <g v-else-if="kind === 'yogurt'">
        <rect x="78" y="78" width="44" height="62" rx="6" fill="#f8fafc" stroke="#fecdd3" />
        <rect x="78" y="78" width="44" height="16" fill="#fb7185" />
        <ellipse cx="100" cy="146" rx="28" ry="6" fill="#fecdd3" />
      </g>
      <g v-else-if="kind === 'rice'">
        <path d="M64 78 H136 L126 156 H74 Z" fill="#f5f0e6" stroke="#d6c7a1" />
        <ellipse cx="100" cy="78" rx="36" ry="10" fill="#e7d7b1" />
        <text x="100" y="124" text-anchor="middle" font-size="16" fill="#a16207">米</text>
      </g>
      <g v-else-if="kind === 'nuts'">
        <ellipse cx="86" cy="110" rx="22" ry="16" fill="#d6a15a" />
        <ellipse cx="118" cy="102" rx="20" ry="14" fill="#c4843a" />
        <ellipse cx="104" cy="132" rx="18" ry="13" fill="#e0b56a" />
      </g>
      <g v-else-if="kind === 'water'">
        <path d="M82 48 H118 L112 156 H88 Z" fill="#dbeafe" stroke="#93c5fd" />
        <rect x="88" y="78" width="24" height="36" fill="#ef4444" />
      </g>
      <g v-else-if="kind === 'noodle'">
        <path d="M58 92 H142 L132 150 H68 Z" fill="#f8fafc" stroke="#e7e5e4" />
        <path d="M72 110 Q90 100 108 112 T140 108" fill="none" stroke="#f59e0b" stroke-width="4" />
        <path d="M70 124 Q96 116 120 126" fill="none" stroke="#fbbf24" stroke-width="4" />
      </g>
      <g v-else-if="kind === 'jerky'">
        <rect x="58" y="78" width="84" height="52" rx="6" fill="#7f1d1d" />
        <rect x="70" y="90" width="60" height="8" rx="2" fill="#fecaca" opacity="0.5" />
      </g>
      <g v-else-if="kind === 'cracker'">
        <rect x="62" y="78" width="76" height="52" rx="8" fill="#fde68a" stroke="#f59e0b" />
        <circle cx="86" cy="98" r="3" fill="#f59e0b" />
        <circle cx="108" cy="110" r="3" fill="#f59e0b" />
        <circle cx="122" cy="94" r="3" fill="#f59e0b" />
      </g>
      <g v-else-if="kind === 'run'">
        <path d="M46 126 Q70 96 120 108 L150 118 Q140 138 96 140 Q60 142 46 126 Z" fill="#111827" />
        <path d="M78 116 L118 112" stroke="#ef4444" stroke-width="4" />
      </g>
      <g v-else-if="kind === 'bball-shoe'">
        <path d="M46 124 Q72 90 128 104 L154 116 Q142 140 96 142 Q58 142 46 124 Z" fill="#ea580c" />
        <path d="M70 116 L120 108" stroke="#fff" stroke-width="3" />
      </g>
      <g v-else-if="kind === 'mat'">
        <rect x="48" y="70" width="104" height="64" rx="8" fill="#14b8a6" transform="rotate(-8 100 102)" />
        <rect x="62" y="84" width="76" height="36" rx="4" fill="#5eead4" transform="rotate(-8 100 102)" />
      </g>
      <g v-else-if="kind === 'racket'">
        <ellipse cx="100" cy="78" rx="28" ry="36" fill="none" stroke="#111827" stroke-width="6" />
        <line x1="84" y1="78" x2="116" y2="78" stroke="#9ca3af" />
        <line x1="100" y1="50" x2="100" y2="106" stroke="#9ca3af" />
        <rect x="96" y="112" width="8" height="42" rx="3" fill="#44403c" />
      </g>
      <g v-else-if="kind === 'bottle'">
        <rect x="86" y="40" width="28" height="14" rx="3" fill="#64748b" />
        <path d="M82 54 H118 L112 160 H88 Z" fill="#bae6fd" stroke="#38bdf8" />
      </g>
      <g v-else-if="kind === 'shell'">
        <path d="M60 78 L82 56 H118 L140 78 L132 154 H68 Z" fill="#166534" />
        <path d="M90 56 L100 80 L110 56" fill="#14532d" />
      </g>
      <g v-else-if="kind === 'ball'">
        <circle cx="100" cy="104" r="42" fill="#f97316" />
        <path d="M70 86 Q100 104 130 86 M70 122 Q100 104 130 122 M100 62 V146" fill="none" stroke="#111827" stroke-width="3" />
      </g>
      <g v-else-if="kind === 'pack'">
        <rect x="70" y="58" width="60" height="86" rx="8" fill="#1d4ed8" />
        <path d="M82 58 V46 Q100 32 118 46 V58" fill="none" stroke="#1e3a8a" stroke-width="6" />
        <rect x="88" y="86" width="24" height="16" rx="3" fill="#bfdbfe" />
      </g>
      <g v-else-if="kind === 'lamp'">
        <path d="M70 92 H130 L118 70 H82 Z" fill="#f8fafc" stroke="#cbd5e1" />
        <rect x="96" y="92" width="8" height="40" fill="#94a3b8" />
        <rect x="78" y="132" width="44" height="8" rx="3" fill="#64748b" />
        <path d="M78 78 Q100 48 122 78" fill="none" stroke="#fbbf24" stroke-width="3" />
      </g>
      <g v-else-if="kind === 'bed'">
        <rect x="48" y="78" width="104" height="64" rx="6" fill="#e0e7ff" />
        <rect x="56" y="86" width="40" height="24" rx="4" fill="#fff" />
        <rect x="102" y="86" width="40" height="24" rx="4" fill="#fff" />
      </g>
      <g v-else-if="kind === 'detergent'">
        <path d="M78 64 H122 L114 160 H86 Z" fill="#bfdbfe" stroke="#60a5fa" />
        <rect x="90" y="48" width="20" height="16" fill="#2563eb" />
        <circle cx="100" cy="110" r="14" fill="#1d4ed8" />
      </g>
      <g v-else-if="kind === 'box'">
        <path d="M48 86 L100 64 L152 86 L100 108 Z" fill="#fde68a" />
        <path d="M48 86 V130 L100 152 V108 Z" fill="#f59e0b" />
        <path d="M152 86 V130 L100 152 V108 Z" fill="#d97706" />
      </g>
      <g v-else-if="kind === 'wok'">
        <path d="M48 110 Q100 168 152 110" fill="#94a3b8" />
        <rect x="146" y="96" width="28" height="8" rx="3" fill="#334155" transform="rotate(20 146 96)" />
      </g>
      <g v-else-if="kind === 'pillow'">
        <ellipse cx="100" cy="108" rx="62" ry="36" fill="#fff7ed" stroke="#fdba74" stroke-width="3" />
        <path d="M58 108 Q100 86 142 108" fill="none" stroke="#fb923c" stroke-width="3" />
      </g>
      <g v-else-if="kind === 'tissue'">
        <rect x="58" y="88" width="84" height="52" rx="6" fill="#38bdf8" />
        <path d="M78 88 Q100 58 122 88" fill="#fff" stroke="#bae6fd" />
        <rect x="70" y="104" width="60" height="8" rx="2" fill="#e0f2fe" />
      </g>
      <g v-else>
        <rect x="64" y="70" width="72" height="60" rx="6" fill="#fff" stroke="#d1d5db" />
      </g>
    </svg>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{ name: string }>();

const kind = computed(() => {
  const name = props.name || "";
  const rules: [string, string][] = [
    ["手机", "phone"],
    ["冰箱", "fridge"],
    ["洗衣机", "washer"],
    ["空调", "ac"],
    ["微波炉", "microwave"],
    ["电视", "tv"],
    ["豆浆机", "soy"],
    ["风扇", "fan"],
    ["热水器", "heater"],
    ["卫衣", "hoodie"],
    ["牛仔裤", "jeans"],
    ["羽绒服", "coat"],
    ["短袖", "shirt"],
    ["帆布鞋", "shoes"],
    ["双肩背包", "bag"],
    ["围巾", "scarf"],
    ["休闲裤", "pants"],
    ["牛奶", "milk"],
    ["酸奶", "yogurt"],
    ["大米", "rice"],
    ["坚果", "nuts"],
    ["天然水", "water"],
    ["牛肉面", "noodle"],
    ["猪肉脯", "jerky"],
    ["雪饼", "cracker"],
    ["跑步鞋", "run"],
    ["篮球鞋", "bball-shoe"],
    ["瑜伽垫", "mat"],
    ["羽毛球", "racket"],
    ["水壶", "bottle"],
    ["冲锋衣", "shell"],
    ["篮球", "ball"],
    ["登山背包", "pack"],
    ["台灯", "lamp"],
    ["四件套", "bed"],
    ["洗衣液", "detergent"],
    ["收纳箱", "box"],
    ["炒锅", "wok"],
    ["乳胶枕", "pillow"],
    ["抽纸", "tissue"],
  ];
  return rules.find(([word]) => name.includes(word))?.[1] || "tissue";
});

const body = computed(() => {
  const name = props.name || "";
  if (name.includes("幻夜黑") || name.includes("黑色")) return "#1c1c1e";
  if (name.includes("深海蓝")) return "#163a66";
  if (name.includes("白色")) return "#f5f5f5";
  if (name.includes("熔岩橙") || name.includes("高达")) return "#e4572e";
  if (name.includes("冰际蓝")) return "#7dd3fc";
  return "#2b2b2b";
});
</script>

<style scoped>
.shot { width: 100%; height: 100%; }
.shot svg { width: 100%; height: 100%; display: block; }
</style>
