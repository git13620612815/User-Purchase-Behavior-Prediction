<template>
  <div v-if="product" class="page">
    <div class="crumb">
      <span>商品 / {{ product.categoryName }} / {{ product.name }}</span>
      <el-button plain @click="back">返回上一页</el-button>
    </div>
    <section class="detail">
      <img class="gallery" :src="productPhoto(product.skuCode)" :alt="product.name" />
      <div class="info">
        <h2>{{ product.name }}</h2>
        <div class="price-bar">
          <span>价格</span>
          <strong><small>¥</small>{{ formatPrice(product.price) }}</strong>
          <em v-if="!predicting && focusProbability !== null">购买概率 {{ percent(focusProbability) }}</em>
          <em v-else-if="!predicting && focusPurchased">已购买</em>
        </div>
        <p>类目：{{ product.categoryName }}</p>
        <p>编号：{{ product.skuCode }}</p>
        <div class="actions">
          <el-button class="ghost" @click="act('favorite')">收藏</el-button>
          <el-button class="cart" @click="act('cart')">加入购物车</el-button>
          <el-button class="buy" @click="act('purchase')">立即购买</el-button>
        </div>
        <div v-if="done" class="result">
          <span>{{ done }}</span>
          <el-button plain @click="back">返回上一页</el-button>
        </div>
      </div>
    </section>
    <section class="guess">
      <div class="guess-head">
        <h3>最可能购买</h3>
        <span v-if="sourceLabel">{{ sourceLabel }}</span>
      </div>
      <el-alert v-if="statusText" :title="statusText" type="warning" :closable="false" show-icon />
      <div v-if="predicting" class="loading">正在根据你的行为计算购买可能性…</div>
      <div v-else class="guess-grid">
        <article v-for="item in predictions" :key="item.productId" class="mini" @click="open(item.productId)">
          <img class="mini-cover" :src="productPhoto(item.skuCode)" :alt="item.productName" />
          <div class="mini-body">
            <h4>{{ item.productName }}</h4>
            <p class="mini-price"><small>¥</small>{{ formatPrice(item.price) }}</p>
            <p class="prob">购买概率 {{ percent(item.probability) }}</p>
            <p class="reason">{{ item.reason }}</p>
          </div>
        </article>
      </div>
      <el-empty v-if="!predicting && !predictions.length" description="暂时没有可预测的商品" />
    </section>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import http from "../api/http";
import { productPhoto } from "../utils/productPhoto";

const route = useRoute();
const router = useRouter();
const product = ref<any>(null);
const done = ref("");
const predicting = ref(false);
const predictions = ref<any[]>([]);
const focusProbability = ref<number | null>(null);
const focusPurchased = ref(false);
const sourceLabel = ref("");
const statusText = ref("");
let requestSeq = 0;
const labels: Record<string, string> = { favorite: "已收藏", cart: "已加入购物车", purchase: "已记录购买" };
function formatPrice(value: number) {
  return Number(value || 0).toFixed(2);
}
function percent(value: number) {
  return (Number(value || 0) * 100).toFixed(2) + "%";
}
function open(id: number) {
  if (String(id) === String(route.params.id)) return;
  router.push("/products/" + id);
}
function back() {
  if (window.history.state?.back) router.back();
  else router.push("/products");
}
async function recalculate(productId: number, seq: number) {
  predicting.value = true;
  predictions.value = [];
  focusProbability.value = null;
  focusPurchased.value = false;
  sourceLabel.value = "";
  statusText.value = "";
  try {
    const data: any = await http.post("/predictions", { productId });
    if (seq !== requestSeq) return;
    predictions.value = (data.items || []).slice(0, 3);
    focusProbability.value = typeof data.focusProbability === "number" ? data.focusProbability : null;
    focusPurchased.value = Boolean(data.focusPurchased);
    sourceLabel.value = data.sourceLabel || "";
    statusText.value = data.statusText || "";
  } finally {
    if (seq === requestSeq) predicting.value = false;
  }
}
async function load() {
  const seq = ++requestSeq;
  const productId = Number(route.params.id);
  done.value = "";
  product.value = await http.get("/products/" + productId);
  if (seq !== requestSeq) return;
  await recalculate(productId, seq);
}
async function act(behaviorType: string) {
  const productId = product.value.id;
  await http.post("/behaviors", { productId, behaviorType });
  ElMessage.success(labels[behaviorType]);
  const seq = ++requestSeq;
  await recalculate(productId, seq);
  if (seq === requestSeq) done.value = labels[behaviorType];
}
watch(() => route.params.id, load, { immediate: true });
</script>

<style scoped>
.page { display: flex; flex-direction: column; gap: 16px; }
.crumb { display: flex; align-items: center; justify-content: space-between; gap: 12px; color: #888; font-size: 13px; }
.detail { display: grid; grid-template-columns: 360px 1fr; gap: 28px; background: #fff; border-radius: 8px; padding: 24px; }
.gallery { width: 100%; height: 360px; object-fit: contain; border-radius: 8px; background: #f6f6f6; }
.info h2 { margin: 0; font-size: 22px; line-height: 1.4; font-weight: 500; color: #222; }
.info p { color: #666; margin: 8px 0; }
.price-bar { display: flex; align-items: baseline; gap: 16px; margin: 16px 0; padding: 14px 16px; background: #fff4e8; }
.price-bar span { color: #888; }
.price-bar strong { color: #ff5000; font-size: 30px; }
.price-bar em { margin-left: auto; color: #ff5000; font-style: normal; font-size: 16px; font-weight: 600; }
.price-bar small { font-size: 16px; margin-right: 2px; }
.actions { display: flex; gap: 12px; margin-top: 20px; flex-wrap: wrap; }
.ghost { height: 42px; }
.cart { height: 42px; color: #ff5000; border-color: #ff5000; background: #fff; }
.buy { height: 42px; background: #ff5000; border-color: #ff5000; color: #fff; }
.buy:hover, .cart:hover { color: #fff; background: #ff6a00; border-color: #ff6a00; }
.result { display: flex; align-items: center; justify-content: space-between; margin-top: 16px; padding: 12px 14px; background: #fff7f3; color: #d4380d; border-radius: 8px; }
.guess { background: #fff; border-radius: 8px; padding: 20px; }
.guess-head { display: flex; align-items: baseline; justify-content: space-between; margin-bottom: 12px; }
.guess-head h3 { margin: 0; font-size: 18px; }
.guess-head span { color: #999; font-size: 13px; }
.loading { color: #888; padding: 12px 0; }
.guess-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px; }
.mini { display: flex; gap: 12px; border: 1px solid #f2f2f2; border-radius: 8px; overflow: hidden; cursor: pointer; }
.mini:hover { border-color: #ff5000; }
.mini-cover { width: 96px; height: 96px; flex: none; object-fit: contain; background: #f6f6f6; }
.mini-body { padding: 10px 10px 10px 0; min-width: 0; }
.mini-body h4 { margin: 0 0 6px; font-size: 14px; font-weight: 500; line-height: 1.4; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.mini-price { margin: 0; color: #ff5000; font-weight: 700; }
.mini-price small { font-size: 12px; }
.prob { margin: 4px 0; color: #ff5000; font-size: 12px; }
.reason { margin: 0; color: #999; font-size: 12px; }
@media (max-width: 860px) {
  .detail { grid-template-columns: 1fr; }
  .gallery { min-height: 220px; }
}
</style>
