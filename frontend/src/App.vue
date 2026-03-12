<template>
  <div class="app">
    <header class="header">
      <h1 class="title">单词图谱</h1>
      <p class="subtitle">沉浸式刷词 · 点击词汇探索关联</p>
    </header>
    <main class="main">
      <router-view />
    </main>
  </div>
</template>

<script setup>
</script>

<style>
  * {
    box-sizing: border-box;
  }
  body {
    margin: 0;
    background: #fafafa;
    min-height: 100vh;
    color: #1a1a1a;
    font-family: 'Noto Serif SC', 'Source Serif 4', serif;
  }
  .app {
    min-height: 100vh;
    display: flex;
    flex-direction: column;
  }
  .header {
    padding: 1.5rem 2rem;
    text-align: center;
    border-bottom: 1px solid #e0e0e0;
  }
  .title {
    font-size: 1.75rem;
    font-weight: 600;
    margin: 0;
    letter-spacing: 0.05em;
    color: #1a1a1a;
  }
  .subtitle {
    margin: 0.35rem 0 0;
    font-size: 0.9rem;
    color: #666;
  }
  .main {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 0;
    padding: 1rem;
  }
</style>
