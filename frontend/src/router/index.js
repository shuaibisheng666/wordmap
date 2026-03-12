import { createRouter, createWebHistory } from 'vue-router'
import WordMap from '../views/WordMap.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'WordMap', component: WordMap },
  ],
})

export default router
