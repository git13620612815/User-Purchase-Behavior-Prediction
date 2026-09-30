<template>
  <router-view />
</template>

<style>
body {
  margin: 0;
  background: #f3f6f6;
  color: #163033;
  font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
}
.shell { min-height: 100vh; background: #f3f6f6; }
.shell-aside {
  background: #0c2c2e;
  color: #e7f6f4;
  display: flex;
  flex-direction: column;
}
.shell-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 22px 18px 12px;
}
.shell-brand strong { display: block; font-size: 16px; }
.shell-brand small { color: rgba(231, 246, 244, 0.62); }
.shell-mark {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  background: #0f6e6b;
  font-weight: 700;
}
.shell-aside .el-menu {
  border-right: none;
  background: transparent;
  --el-menu-bg-color: transparent;
  --el-menu-text-color: rgba(231, 246, 244, 0.82);
  --el-menu-hover-text-color: #fff;
  --el-menu-active-color: #fff;
  --el-menu-hover-bg-color: rgba(255, 255, 255, 0.08);
}
.shell-aside .el-menu-item-group__title {
  color: rgba(231, 246, 244, 0.42);
  padding-left: 22px;
}
.shell-aside .el-menu-item {
  height: 42px;
  margin: 2px 12px;
  border-radius: 8px;
}
.shell-aside .el-menu-item.is-active { background: #0f6e6b; }
.shell-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 64px;
  padding: 0 24px;
  background: #fff;
  border-bottom: 1px solid #e6eeee;
}
.shell-header h1 { margin: 0; font-size: 18px; font-weight: 650; }
.shell-user { display: flex; align-items: center; gap: 12px; color: #5d7173; }
.shell-main { --el-color-primary: #0f6e6b; padding: 20px 24px; }
.shell-main .el-card { border-radius: 12px; border-color: #e6eeee; }
.toolbar { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin-bottom: 12px; }
.pager { margin-top: 12px; justify-content: flex-end; }
@media (max-width: 860px) {
  .shell { display: block; }
  .shell-aside { width: 100% !important; }
  .shell-header h1 { font-size: 16px; }
}
</style>
