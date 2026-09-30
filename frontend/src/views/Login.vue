<template>
  <div class="page">
    <div class="bg" aria-hidden="true">
      <span class="orb orb-a"></span>
      <span class="orb orb-b"></span>
      <span class="orb orb-c"></span>
      <svg class="net" viewBox="0 0 1200 800" preserveAspectRatio="xMidYMid slice">
        <g stroke="rgba(214,244,240,0.35)" stroke-width="1.2" fill="none">
          <path d="M80 140 L240 220 L180 390 L420 310 L560 180 L780 260 L920 140 L1080 240" />
          <path d="M140 620 L320 540 L480 680 L700 560 L860 700 L1040 580" />
          <path d="M420 310 L480 680" />
          <path d="M560 180 L700 560" />
          <path d="M240 220 L320 540" />
        </g>
        <g fill="#d8f6f2">
          <circle cx="80" cy="140" r="4" />
          <circle cx="240" cy="220" r="5" />
          <circle cx="180" cy="390" r="3.5" />
          <circle cx="420" cy="310" r="5" />
          <circle cx="560" cy="180" r="4" />
          <circle cx="780" cy="260" r="5" />
          <circle cx="920" cy="140" r="3.5" />
          <circle cx="1080" cy="240" r="4" />
          <circle cx="140" cy="620" r="4" />
          <circle cx="320" cy="540" r="5" />
          <circle cx="480" cy="680" r="4" />
          <circle cx="700" cy="560" r="5" />
          <circle cx="860" cy="700" r="3.5" />
          <circle cx="1040" cy="580" r="4" />
        </g>
      </svg>
    </div>
    <div class="panel">
      <section class="intro">
        <div class="mark">购</div>
        <h1>用户购买行为预测</h1>
        <p>记录浏览、收藏、加购和购买，估计接下来可能购买的商品。</p>
        <ul>
          <li>四种行为写入后即可发起预测</li>
          <li>结果来自图神经网络或热门商品</li>
          <li>每条结果带有购买概率和理由</li>
        </ul>
      </section>
      <section class="form-side">
        <h2>登录</h2>
        <p class="sub">使用已注册账号进入系统</p>
        <el-form label-position="top" :model="form" @submit.prevent="submit">
          <el-form-item label="用户名">
            <el-input
              ref="usernameRef"
              v-model="form.username"
              placeholder="请输入用户名"
              autocomplete="username"
              clearable
              @keyup.enter="submit"
            />
          </el-form-item>
          <el-form-item label="密码">
            <el-input
              v-model="form.password"
              type="password"
              placeholder="请输入密码"
              autocomplete="current-password"
              show-password
              @keyup.enter="submit"
            />
          </el-form-item>
          <el-button class="submit" type="primary" native-type="submit" :loading="loading" :disabled="!canSubmit">
            登录
          </el-button>
        </el-form>
        <div class="demo">
          <span>演示账号</span>
          <button type="button" @click="fill('admin', 'Admin12345')">管理员</button>
          <button type="button" @click="fill('user01', 'User12345')">普通用户</button>
        </div>
        <div class="extra">没有账号？<router-link to="/register">注册</router-link></div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import http from "../api/http";

const router = useRouter();
const loading = ref(false);
const usernameRef = ref();
const form = reactive({
  username: localStorage.getItem("lastUsername") || "",
  password: "",
});
const canSubmit = computed(() => form.username.trim() !== "" && form.password !== "" && !loading.value);

onMounted(() => {
  nextTick(() => usernameRef.value?.focus?.());
});

function fill(username: string, password: string) {
  form.username = username;
  form.password = password;
}

async function submit() {
  if (!form.username.trim() || !form.password) {
    ElMessage.warning("请输入用户名和密码");
    return;
  }
  loading.value = true;
  try {
    const data: any = await http.post("/auth/login", {
      username: form.username.trim(),
      password: form.password,
    });
    localStorage.setItem("token", data.accessToken);
    localStorage.setItem("role", data.role);
    localStorage.setItem("lastUsername", form.username.trim());
    router.push(data.role === "ADMIN" ? "/admin" : "/products");
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.page {
  --el-color-primary: #0f6e6b;
  position: relative;
  isolation: isolate;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  overflow: hidden;
  background:
    radial-gradient(900px 520px at 8% 12%, rgba(46, 196, 182, 0.42), transparent 58%),
    radial-gradient(760px 480px at 92% 88%, rgba(232, 184, 92, 0.28), transparent 55%),
    radial-gradient(640px 420px at 78% 8%, rgba(92, 156, 214, 0.32), transparent 60%),
    linear-gradient(155deg, #07191b 0%, #0d3533 46%, #102844 100%);
}
.page::before {
  content: "";
  position: absolute;
  inset: 0;
  background-image: radial-gradient(rgba(255, 255, 255, 0.28) 1px, transparent 1px);
  background-size: 26px 26px;
  mask-image: radial-gradient(ellipse at center, #000 20%, transparent 72%);
  opacity: 0.28;
  pointer-events: none;
}
.bg {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 0;
}
.orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(8px);
}
.orb-a {
  width: 420px;
  height: 420px;
  left: -80px;
  top: -60px;
  background: radial-gradient(circle, rgba(72, 214, 198, 0.55), rgba(72, 214, 198, 0) 68%);
  animation: drift 16s ease-in-out infinite;
}
.orb-b {
  width: 360px;
  height: 360px;
  right: -40px;
  bottom: -80px;
  background: radial-gradient(circle, rgba(240, 196, 110, 0.42), rgba(240, 196, 110, 0) 70%);
  animation: drift 20s ease-in-out infinite reverse;
}
.orb-c {
  width: 280px;
  height: 280px;
  right: 18%;
  top: 8%;
  background: radial-gradient(circle, rgba(126, 176, 230, 0.4), rgba(126, 176, 230, 0) 70%);
  animation: drift 18s ease-in-out infinite;
}
.net {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  opacity: 0.45;
}
@keyframes drift {
  0%, 100% { transform: translate3d(0, 0, 0); }
  50% { transform: translate3d(18px, 24px, 0); }
}
@media (prefers-reduced-motion: reduce) {
  .orb-a, .orb-b, .orb-c { animation: none; }
}
.panel {
  position: relative;
  z-index: 1;
  width: min(920px, 100%);
  display: grid;
  grid-template-columns: 1.05fr 0.95fr;
  background: #fff;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 24px 70px rgba(0, 0, 0, 0.32);
}
.intro {
  padding: 48px 40px;
  color: #f4fbfa;
  background: linear-gradient(165deg, #124e4c 0%, #0b2f33 100%);
}
.mark {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  background: rgba(255, 255, 255, 0.14);
  font-size: 22px;
  font-weight: 700;
}
.intro h1 {
  margin: 20px 0 12px;
  font-size: 30px;
  line-height: 1.3;
}
.intro p,
.intro li {
  color: rgba(244, 251, 250, 0.86);
  line-height: 1.7;
}
.intro ul {
  margin: 28px 0 0;
  padding-left: 18px;
}
.form-side {
  padding: 48px 40px 36px;
}
.form-side h2 {
  margin: 0;
  font-size: 26px;
  color: #163033;
}
.sub {
  margin: 8px 0 24px;
  color: #6b7c7e;
}
.submit {
  width: 100%;
  height: 40px;
}
.demo {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 18px;
  color: #6b7c7e;
  font-size: 13px;
}
.demo button {
  border: 1px solid #d5e2e1;
  background: #f6fbfa;
  color: #0f6e6b;
  border-radius: 999px;
  padding: 4px 10px;
  cursor: pointer;
}
.demo button:hover {
  background: #e7f5f3;
}
.extra {
  margin-top: 18px;
  text-align: right;
}
.extra a {
  color: #0f6e6b;
}
@media (max-width: 760px) {
  .panel { grid-template-columns: 1fr; }
  .intro { padding: 28px 24px; }
  .intro ul { display: none; }
  .form-side { padding: 28px 24px; }
}
</style>
