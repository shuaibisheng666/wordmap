<template>
  <div class="word-map-page">
    <!-- 首次进入：输入或随机生成 -->
    <div v-if="nodes.length === 0" class="entry">
      <div class="entry-card">
        <p class="entry-title">输入一个英文单词开始</p>
        <div class="entry-controls">
          <input
            v-model="inputWord"
            type="text"
            class="input"
            placeholder="输入一个英文单词"
            @keydown.enter="fetchWord"
          />
          <button class="btn btn-primary" :disabled="loading" @click="fetchWord">
            {{ loading ? '生成中…' : '生成图谱' }}
          </button>
          <button class="btn btn-secondary" :disabled="loading" @click="fetchRandom">
            随机一词
          </button>
        </div>
        <p v-if="error" class="error">{{ error }}</p>
      </div>
    </div>
    <!-- 已有图谱：图谱 + 齿轮设置 -->
    <div v-else class="graph-view">
      <p v-if="error" class="graph-error">
        {{ error }}
        <button type="button" class="graph-error-close" aria-label="关闭" @click="error = ''">×</button>
      </p>
      <button class="btn-settings" type="button" aria-label="设置" @click="settingsOpen = !settingsOpen">
        <svg class="icon-gear" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z"/>
          <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
        </svg>
      </button>
      <!-- 遮罩和设置面板挂到 body，避免被祖先 transform 影响导致 fixed 定位错乱 -->
      <Teleport to="body">
        <div
          v-show="settingsOpen"
          class="settings-backdrop"
          aria-hidden="true"
          @click="settingsOpen = false"
        />
        <div class="settings-panel" :class="{ open: settingsOpen }">
        <div class="settings-head">
          <span>设置</span>
          <button type="button" class="settings-close" aria-label="关闭" @click="settingsOpen = false">×</button>
        </div>
        <div class="settings-section">
          <label class="settings-check"><input v-model="showEdgeLabels" type="checkbox" /> 显示关系</label>
        </div>
        <div class="settings-section">
          <div class="settings-label">近义线型</div>
          <label class="settings-radio"><input v-model="lineStyleSynonym" type="radio" value="solid" /> 实线</label>
          <label class="settings-radio"><input v-model="lineStyleSynonym" type="radio" value="dashed" /> 虚线</label>
          <label class="settings-radio"><input v-model="lineStyleSynonym" type="radio" value="dotted" /> 点线</label>
        </div>
        <div class="settings-section">
          <div class="settings-label">反义线型</div>
          <label class="settings-radio"><input v-model="lineStyleAntonym" type="radio" value="solid" /> 实线</label>
          <label class="settings-radio"><input v-model="lineStyleAntonym" type="radio" value="dashed" /> 虚线</label>
          <label class="settings-radio"><input v-model="lineStyleAntonym" type="radio" value="dotted" /> 点线</label>
        </div>
        <div class="settings-section">
          <div class="settings-label">形近词线型</div>
          <label class="settings-radio"><input v-model="lineStyleSpelling" type="radio" value="solid" /> 实线</label>
          <label class="settings-radio"><input v-model="lineStyleSpelling" type="radio" value="dashed" /> 虚线</label>
          <label class="settings-radio"><input v-model="lineStyleSpelling" type="radio" value="dotted" /> 点线</label>
        </div>
        <div class="settings-section settings-section-llm">
          <div class="settings-label">大模型设置</div>
          <label class="settings-field">
            <span class="settings-field-label">Base URL</span>
            <input v-model="llmBaseUrl" type="text" class="settings-input" placeholder="https://api.siliconflow.cn/v1" />
          </label>
          <label class="settings-field">
            <span class="settings-field-label">API Key</span>
            <input v-model="llmApiKey" type="password" class="settings-input" placeholder="sk-..." autocomplete="off" />
          </label>
          <label class="settings-field">
            <span class="settings-field-label">Model</span>
            <input v-model="llmModelName" type="text" class="settings-input" placeholder="deepseek-ai/DeepSeek-V3" />
          </label>
          <button type="button" class="btn btn-primary settings-llm-btn" :disabled="llmSaving" @click="saveLlmSettings">
            {{ llmSaving ? '保存中…' : '保存' }}
          </button>
        </div>
        <button class="btn btn-secondary settings-btn" @click="resetToEntry">换词</button>
        </div>
      </Teleport>
      <div ref="graphContainer" class="graph-container"></div>
    </div>
    <div
      v-show="tooltipVisible"
      class="node-tooltip"
      :style="{ left: tooltipX + 'px', top: tooltipY + 'px' }"
    >
      <span class="node-tooltip-word">{{ tooltipWord }}</span>
      <span v-if="tooltipDefinition" class="node-tooltip-definition">{{ tooltipDefinition }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import * as d3 from 'd3'
import { getWordRelations, getRandomWord, getLlmConfig, saveLlmConfig } from '../api/word'

const inputWord = ref('')
const loading = ref(false)
const error = ref('')
const graphContainer = ref(null)
// 设置面板
const settingsOpen = ref(false)
const showEdgeLabels = ref(true)
// 点击某词展开关系时，该词 id（用于在其下方显示「关系词生成中」）
const expandingWordId = ref('')
const lineStyleSynonym = ref('solid')
const lineStyleAntonym = ref('dashed')
const lineStyleSpelling = ref('dotted')
// 大模型设置
const llmBaseUrl = ref('')
const llmApiKey = ref('')
const llmModelName = ref('')
const llmSaving = ref(false)
// 节点悬停提示（翻译/释义）
const tooltipVisible = ref(false)
const tooltipWord = ref('')
const tooltipDefinition = ref('')
const tooltipX = ref(0)
const tooltipY = ref(0)

// 图数据：节点与边
const nodes = ref([])
const links = ref([])
let simulation = null
let svg = null
let zoomG = null
let linkGroups = null
let nodeElements = null
let linkElements = null
let linkLabelElements = null
let labelGroups = null
let zoomBehavior = null

// 边上关系类型中文
const typeLabel = { synonym: '近义', antonym: '反义', spelling: '形近' }
// 显示全部关系边（已去掉按类型过滤）
const visibleLinks = computed(() => links.value)
// 按关系类型返回线型 stroke-dasharray
function getDasharray(type) {
  const s = type === 'synonym' ? lineStyleSynonym.value : type === 'antonym' ? lineStyleAntonym.value : type === 'spelling' ? lineStyleSpelling.value : 'solid'
  if (s === 'dashed') return '8,4'
  if (s === 'dotted') return '2,3'
  return 'none'
}
// 节点颜色（彩色）
const NODE_COLORS = ['#2c5282', '#7cb87c', '#c75c5c', '#b89c5c', '#8b5cf6', '#e8796b', '#5c8bd6']
function nodeColor(d, i) {
  if (d.isCenter) return '#2c5282'
  return NODE_COLORS[i % NODE_COLORS.length]
}

function curvedPath(d) {
  const sx = d.source.x
  const sy = d.source.y
  const tx = d.target.x
  const ty = d.target.y
  const midX = (sx + tx) / 2
  const midY = (sy + ty) / 2
  const dx = tx - sx
  const dy = ty - sy
  const len = Math.hypot(dx, dy) || 1
  const offset = 28
  const cx = midX + (-dy / len) * offset
  const cy = midY + (dx / len) * offset
  return `M ${sx} ${sy} Q ${cx} ${cy} ${tx} ${ty}`
}

function curvedMidpoint(d) {
  const sx = d.source.x
  const sy = d.source.y
  const tx = d.target.x
  const ty = d.target.y
  const midX = (sx + tx) / 2
  const midY = (sy + ty) / 2
  const dx = tx - sx
  const dy = ty - sy
  const len = Math.hypot(dx, dy) || 1
  const offset = 28
  const cx = midX + (-dy / len) * offset
  const cy = midY + (dx / len) * offset
  return { x: 0.25 * sx + 0.5 * cx + 0.25 * tx, y: 0.25 * sy + 0.5 * cy + 0.25 * ty }
}

// 已有节点 id 集合，避免重复
const nodeIds = ref(new Set())
// 已有边 key 集合，避免重复边
const linkKeys = ref(new Set())
// 已请求展开过的单词，避免重复请求；未在此集合中的节点点击时会请求并展开
const expandedWordIds = ref(new Set())
// 拖拽中不触发点击展开
let isDragging = false

function linkKey(a, b, type) {
  const [x, y] = [a, b].sort()
  return `${x}-${y}-${type}`
}

function addWordToGraph(data) {
  const center = data.word.toLowerCase().trim()
  const newNodes = []
  const newLinks = []

  if (!nodeIds.value.has(center)) {
    nodeIds.value.add(center)
    newNodes.push({ id: center, isCenter: true, definition: data.definition || '' })
  } else {
    const n = nodes.value.find((node) => node.id === center)
    if (n) n.definition = data.definition || ''
  }

  const addRel = (item, type) => {
    const w = (typeof item === 'object' && item && item.word != null) ? String(item.word) : String(item)
    const def = (typeof item === 'object' && item && 'definition' in item) ? String(item.definition || '') : ''
    const word = w.toLowerCase().trim()
    if (!word || word === center) return
    if (!nodeIds.value.has(word)) {
      nodeIds.value.add(word)
      newNodes.push({ id: word, isCenter: false, definition: def })
    } else if (def) {
      const n = nodes.value.find((node) => node.id === word)
      if (n) n.definition = def
    }
    const key = linkKey(center, word, type)
    if (!linkKeys.value.has(key)) {
      linkKeys.value.add(key)
      newLinks.push({ source: center, target: word, type })
    }
  }

  ;(data.synonyms || []).forEach((item) => addRel(item, 'synonym'))
  ;(data.antonyms || []).forEach((item) => addRel(item, 'antonym'))
  ;(data.similar_spelling || []).forEach((item) => addRel(item, 'spelling'))

  if (newNodes.length) nodes.value = [...nodes.value, ...newNodes]
  if (newLinks.length) links.value = [...links.value, ...newLinks]
  return { newNodes, newLinks }
}

function drawGraph() {
  if (!graphContainer.value) return
  d3.select(graphContainer.value).selectAll('*').remove()

  const fallbackWidth = Math.min(1600, Math.max(400, (typeof window !== 'undefined' ? window.innerWidth : 800) - 48))
  const fallbackHeight = Math.max(400, (typeof window !== 'undefined' ? window.innerHeight : 600) - 140)
  const width = Math.max(graphContainer.value.clientWidth || 0, fallbackWidth)
  const height = Math.max(graphContainer.value.clientHeight || 0, fallbackHeight)

  svg = d3
    .select(graphContainer.value)
    .append('svg')
    .attr('width', width)
    .attr('height', height)
    .attr('viewBox', [0, 0, width, height])

  // 画布缩放与平移
  zoomG = svg.append('g')
  zoomBehavior = d3.zoom()
    .scaleExtent([0.2, 4])
    .on('zoom', (event) => zoomG.attr('transform', event.transform))
  svg.call(zoomBehavior)

  const g = zoomG.append('g')

  simulation = d3
    .forceSimulation(nodes.value)
    .force(
      'link',
      d3.forceLink(links.value).id((d) => d.id).distance(100)
    )
    .force('charge', d3.forceManyBody().strength(-260))
    .force('center', d3.forceCenter(width / 2, height / 2))
    .force('collision', d3.forceCollide().radius(36))

  linkGroups = g
    .append('g')
    .selectAll('g.link-group')
    .data(visibleLinks.value)
    .join('g')
    .attr('class', 'link-group')
  linkElements = linkGroups.append('path')
    .attr('fill', 'none')
    .attr('stroke', '#999')
    .attr('stroke-width', 1.2)
    .attr('stroke-dasharray', (d) => getDasharray(d.type))
  linkLabelElements = linkGroups.append('text')
    .attr('text-anchor', 'middle')
    .attr('dy', '0.35em')
    .attr('font-size', 10)
    .attr('fill', '#333')
    .attr('visibility', showEdgeLabels.value ? 'visible' : 'hidden')
    .style('pointer-events', 'none')
    .style('font-family', 'Noto Serif SC, serif')
    .text((d) => typeLabel[d.type] || d.type)

  const drag = d3.drag()
    .on('start', (event, d) => {
      if (!event.active) simulation.alphaTarget(0.3).restart()
      d.fx = d.x
      d.fy = d.y
    })
    .on('drag', (event, d) => {
      isDragging = true
      d.fx = event.x
      d.fy = event.y
    })
    .on('end', (event, d) => {
      if (!event.active) simulation.alphaTarget(0)
      d.fx = null
      d.fy = null
      setTimeout(() => { isDragging = false }, 0)
    })

  nodeElements = g
    .append('g')
    .selectAll('circle')
    .data(nodes.value)
    .join('circle')
    .attr('r', (d) => (d.isCenter ? 6 : 5))
    .attr('fill', nodeColor)
    .attr('stroke', (d) => d3.color(nodeColor(d))?.darker(0.5)?.toString() || '#333')
    .attr('stroke-width', 1)
    .style('cursor', 'grab')
    .call(drag)
    .on('click', (event, d) => {
      if (isDragging) return
      onNodeClick(d.id)
    })
    .on('mouseenter', (event, d) => {
      tooltipWord.value = d.id
      tooltipX.value = event.pageX
      tooltipY.value = event.pageY
      tooltipVisible.value = true
      if (d.definition) {
        tooltipDefinition.value = d.definition
      } else {
        tooltipDefinition.value = '加载中…'
        getWordRelations(d.id).then((data) => {
          if (data.error) return
          d.definition = data.definition || ''
          if (tooltipWord.value === d.id) tooltipDefinition.value = d.definition
        })
      }
    })
    .on('mousemove', (event) => {
      tooltipX.value = event.pageX
      tooltipY.value = event.pageY
    })
    .on('mouseleave', () => {
      tooltipVisible.value = false
    })

  labelGroups = g
    .append('g')
    .selectAll('g')
    .data(nodes.value)
    .join('g')
    .attr('class', 'node-label')
  labelGroups.append('text')
    .attr('class', 'node-word')
    .attr('text-anchor', 'start')
    .attr('dx', 8)
    .attr('dy', '0.35em')
    .attr('font-size', (d) => (d.isCenter ? 13 : 11))
    .attr('fill', '#1a1a1a')
    .style('pointer-events', 'none')
    .style('font-family', 'Source Serif 4, Noto Serif SC, serif')
    .text((d) => d.id)
  labelGroups.append('text')
    .attr('class', 'node-loading')
    .attr('text-anchor', 'start')
    .attr('dx', 8)
    .attr('dy', '1.2em')
    .attr('font-size', 9)
    .attr('fill', '#999')
    .style('pointer-events', 'none')
    .style('font-family', 'Noto Serif SC, serif')
    .text('')

  simulation.on('tick', () => {
    linkElements.attr('d', curvedPath).attr('stroke-dasharray', (d) => getDasharray(d.type))
    linkLabelElements.each(function (d) {
      const m = curvedMidpoint(d)
      d3.select(this).attr('x', m.x).attr('y', m.y)
    }).attr('visibility', showEdgeLabels.value ? 'visible' : 'hidden')
    nodeElements.attr('cx', (d) => d.x).attr('cy', (d) => d.y)
    labelGroups.attr('transform', (d) => `translate(${d.x},${d.y})`)
    labelGroups.select('text.node-loading')
      .text((d) => (loading.value && expandingWordId.value === d.id ? '关系词生成中' : ''))
      .attr('visibility', (d) => (loading.value && expandingWordId.value === d.id ? 'visible' : 'hidden'))
  })
}

function updateGraph() {
  if (!simulation || !linkElements || !nodeElements || !labelGroups) {
    drawGraph()
    return
  }
  linkGroups = zoomG.select('g').selectAll('g.link-group')
    .data(visibleLinks.value)
    .join(
      (enter) => {
        const g = enter.append('g').attr('class', 'link-group')
        g.append('path').attr('fill', 'none').attr('stroke', '#999').attr('stroke-width', 1.2).attr('stroke-dasharray', (d) => getDasharray(d.type))
        g.append('text')
          .attr('text-anchor', 'middle')
          .attr('dy', '0.35em')
          .attr('font-size', 10)
          .attr('fill', '#333')
          .attr('visibility', showEdgeLabels.value ? 'visible' : 'hidden')
          .style('pointer-events', 'none')
          .style('font-family', 'Noto Serif SC, serif')
          .text((d) => typeLabel[d.type] || d.type)
        return g
      }
    )
  linkElements = linkGroups.select('path').attr('stroke-dasharray', (d) => getDasharray(d.type))
  linkLabelElements = linkGroups.select('text').attr('visibility', showEdgeLabels.value ? 'visible' : 'hidden')

  const drag = d3.drag()
    .on('start', (event, d) => {
      if (!event.active) simulation.alphaTarget(0.3).restart()
      d.fx = d.x
      d.fy = d.y
    })
    .on('drag', (event, d) => {
      isDragging = true
      d.fx = event.x
      d.fy = event.y
    })
    .on('end', (event, d) => {
      if (!event.active) simulation.alphaTarget(0)
      d.fx = null
      d.fy = null
      setTimeout(() => { isDragging = false }, 0)
    })

  nodeElements = nodeElements.data(nodes.value).join('circle')
  nodeElements
    .attr('r', (d) => (d.isCenter ? 6 : 5))
    .attr('fill', nodeColor)
    .attr('stroke', (d) => d3.color(nodeColor(d))?.darker(0.5)?.toString() || '#333')
    .attr('stroke-width', 1)
    .style('cursor', 'grab')
    .call(drag)
    .on('click', (event, d) => {
      if (isDragging) return
      onNodeClick(d.id)
    })
    .on('mouseenter', (event, d) => {
      tooltipWord.value = d.id
      tooltipX.value = event.pageX
      tooltipY.value = event.pageY
      tooltipVisible.value = true
      if (d.definition) {
        tooltipDefinition.value = d.definition
      } else {
        tooltipDefinition.value = '加载中…'
        getWordRelations(d.id).then((data) => {
          if (data.error) return
          d.definition = data.definition || ''
          if (tooltipWord.value === d.id) tooltipDefinition.value = d.definition
        })
      }
    })
    .on('mousemove', (event) => {
      tooltipX.value = event.pageX
      tooltipY.value = event.pageY
    })
    .on('mouseleave', () => {
      tooltipVisible.value = false
    })

  labelGroups = labelGroups.data(nodes.value).join(
    (enter) => {
      const g = enter.append('g').attr('class', 'node-label')
      g.append('text').attr('class', 'node-word').attr('text-anchor', 'start').attr('dx', 8).attr('dy', '0.35em').attr('font-size', (d) => (d.isCenter ? 13 : 11)).attr('fill', '#1a1a1a').style('pointer-events', 'none').style('font-family', 'Source Serif 4, Noto Serif SC, serif').text((d) => d.id)
      g.append('text').attr('class', 'node-loading').attr('text-anchor', 'start').attr('dx', 8).attr('dy', '1.2em').attr('font-size', 9).attr('fill', '#999').style('pointer-events', 'none').style('font-family', 'Noto Serif SC, serif').text('')
      return g
    }
  )
  labelGroups.select('text.node-definition').remove()
  labelGroups.select('text.node-word').text((d) => d.id).attr('font-size', (d) => (d.isCenter ? 13 : 11))
  labelGroups.select('text.node-loading').text((d) => (loading.value && expandingWordId.value === d.id ? '关系词生成中' : '')).attr('visibility', (d) => (loading.value && expandingWordId.value === d.id ? 'visible' : 'hidden'))

  simulation.nodes(nodes.value)
  simulation.force('link').links(links.value)
  simulation.on('tick', () => {
    linkElements.attr('d', curvedPath).attr('stroke-dasharray', (d) => getDasharray(d.type))
    linkLabelElements.each(function (d) {
      const m = curvedMidpoint(d)
      d3.select(this).attr('x', m.x).attr('y', m.y)
    }).attr('visibility', showEdgeLabels.value ? 'visible' : 'hidden')
    nodeElements.attr('cx', (d) => d.x).attr('cy', (d) => d.y)
    labelGroups.attr('transform', (d) => `translate(${d.x},${d.y})`)
    labelGroups.select('text.node-loading')
      .text((d) => (loading.value && expandingWordId.value === d.id ? '关系词生成中' : ''))
      .attr('visibility', (d) => (loading.value && expandingWordId.value === d.id ? 'visible' : 'hidden'))
  })
  simulation.alpha(0.4).restart()
}

// 设置变更时重绘边的显示
watch([showEdgeLabels, lineStyleSynonym, lineStyleAntonym, lineStyleSpelling], () => {
  if (nodes.value.length && linkGroups) {
    linkGroups = zoomG.select('g').selectAll('g.link-group')
      .data(visibleLinks.value)
      .join(
        (enter) => {
          const g = enter.append('g').attr('class', 'link-group')
          g.append('path').attr('fill', 'none').attr('stroke', '#999').attr('stroke-width', 1.2).attr('stroke-dasharray', (d) => getDasharray(d.type))
          g.append('text').attr('text-anchor', 'middle').attr('dy', '0.35em').attr('font-size', 10).attr('fill', '#333').attr('visibility', showEdgeLabels.value ? 'visible' : 'hidden').style('pointer-events', 'none').style('font-family', 'Noto Serif SC, serif').text((d) => typeLabel[d.type] || d.type)
          return g
        },
        (update) => update,
        (exit) => exit.remove()
      )
    linkElements = linkGroups.select('path').attr('stroke-dasharray', (d) => getDasharray(d.type))
    linkLabelElements = linkGroups.select('text').attr('visibility', showEdgeLabels.value ? 'visible' : 'hidden')
  }
})

async function onNodeClick(word) {
  if (loading.value) return
  if (expandedWordIds.value.has(word)) return // 已展开过，避免重复请求
  expandingWordId.value = word
  loading.value = true
  error.value = ''
  try {
    const data = await getWordRelations(word)
    if (data.error) throw new Error(data.error)
    addWordToGraph(data)
    expandedWordIds.value.add(word)
    updateGraph()
  } catch (e) {
    error.value = e.message || '获取失败'
  } finally {
    loading.value = false
    expandingWordId.value = ''
  }
}

async function fetchWord() {
  const word = inputWord.value.trim()
  if (!word) {
    error.value = '请输入单词'
    return
  }
  loading.value = true
  error.value = ''
  nodes.value = []
  links.value = []
  nodeIds.value = new Set()
  linkKeys.value = new Set()
  expandedWordIds.value = new Set()
  try {
    const data = await getWordRelations(word)
    if (data.error) throw new Error(data.error)
    addWordToGraph(data)
    expandedWordIds.value.add(data.word.toLowerCase().trim())
    await nextTick()
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        if (graphContainer.value && nodes.value.length) drawGraph()
      })
    })
  } catch (e) {
    error.value = e.message || '获取失败'
  } finally {
    loading.value = false
  }
}

async function fetchRandom() {
  inputWord.value = ''
  loading.value = true
  error.value = ''
  nodes.value = []
  links.value = []
  nodeIds.value = new Set()
  linkKeys.value = new Set()
  expandedWordIds.value = new Set()
  try {
    const data = await getRandomWord()
    if (data.error) throw new Error(data.error)
    inputWord.value = data.word
    addWordToGraph(data)
    expandedWordIds.value.add(data.word.toLowerCase().trim())
    await nextTick()
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        if (graphContainer.value && nodes.value.length) drawGraph()
      })
    })
  } catch (e) {
    error.value = e.message || '获取失败'
  } finally {
    loading.value = false
  }
}

function resetToEntry() {
  if (simulation) simulation.stop()
  simulation = null
  if (graphContainer.value) d3.select(graphContainer.value).selectAll('*').remove()
  nodes.value = []
  links.value = []
  nodeIds.value = new Set()
  linkKeys.value = new Set()
  expandedWordIds.value = new Set()
  inputWord.value = ''
  error.value = ''
  tooltipVisible.value = false
  expandingWordId.value = ''
}

watch([nodes, links], () => {}, { deep: true })

async function loadLlmConfig() {
  try {
    const c = await getLlmConfig()
    llmBaseUrl.value = c.base_url ?? ''
    llmApiKey.value = c.api_key ?? ''
    llmModelName.value = c.model ?? ''
  } catch (_) {}
}
async function saveLlmSettings() {
  llmSaving.value = true
  try {
    await saveLlmConfig({
      base_url: llmBaseUrl.value?.trim() || undefined,
      api_key: llmApiKey.value?.trim() || undefined,
      model: llmModelName.value?.trim() || undefined,
    })
  } finally {
    llmSaving.value = false
  }
}
watch(settingsOpen, (open) => {
  if (open) loadLlmConfig()
})

const onResize = () => {
  if (graphContainer.value && nodes.value.length) drawGraph()
}
onMounted(() => {
  window.addEventListener('resize', onResize)
})

onBeforeUnmount(() => {
  if (simulation) simulation.stop()
  window.removeEventListener('resize', onResize)
})
</script>

<style scoped>
  .word-map-page {
    max-width: 1600px;
    margin: 0 auto;
    padding: 1rem;
    position: relative;
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 0;
  }
  .entry {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 60vh;
    padding: 2rem;
  }
  .entry-card {
    width: 100%;
    max-width: 420px;
    padding: 2rem;
    background: #fff;
    border: 1px solid #e0e0e0;
    border-radius: 12px;
    box-shadow: 0 2px 16px rgba(0,0,0,0.06);
  }
  .entry-title {
    margin: 0 0 1.5rem;
    font-size: 1.1rem;
    color: #333;
    text-align: center;
  }
  .entry-controls {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }
  .entry-controls .input {
    width: 100%;
  }
  .entry-controls .btn {
    width: 100%;
  }
  .graph-view {
    position: relative;
    padding-top: 0.25rem;
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 0;
  }
  .graph-error {
    position: absolute;
    top: 0.5rem;
    left: 0.5rem;
    right: 3rem;
    margin: 0;
    padding: 0.5rem 2rem 0.5rem 0.75rem;
    background: #fff5f5;
    border: 1px solid #f5c6cb;
    border-radius: 8px;
    color: #721c24;
    font-size: 0.9rem;
    z-index: 10;
  }
  .graph-error-close {
    position: absolute;
    top: 0.35rem;
    right: 0.35rem;
    width: 24px;
    height: 24px;
    padding: 0;
    border: none;
    background: transparent;
    color: #721c24;
    font-size: 1.2rem;
    line-height: 1;
    cursor: pointer;
  }
  .graph-error-close:hover {
    opacity: 0.8;
  }
  .btn-settings {
    position: absolute;
    top: 0.5rem;
    right: 0.5rem;
    width: 40px;
    height: 40px;
    padding: 0;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    background: #fff;
    color: #333;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 10;
  }
  .btn-settings:hover {
    background: #f5f5f5;
  }
  .icon-gear {
    width: 22px;
    height: 22px;
  }
  .settings-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.2);
    z-index: 18;
    cursor: pointer;
  }
  .settings-panel {
    position: fixed;
    top: 0;
    right: 0;
    width: 260px;
    height: 100vh;
    background: #fff;
    border-left: 1px solid #e0e0e0;
    box-shadow: -4px 0 20px rgba(0,0,0,0.06);
    padding: 1.5rem;
    transform: translateX(100%);
    transition: transform 0.2s ease;
    z-index: 20;
    overflow-y: auto;
  }
  .settings-panel.open {
    transform: translateX(0);
  }
  .settings-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 1rem;
    font-weight: 600;
    margin-bottom: 1.25rem;
    color: #1a1a1a;
  }
  .settings-close {
    width: 32px;
    height: 32px;
    padding: 0;
    border: none;
    border-radius: 6px;
    background: transparent;
    color: #666;
    font-size: 1.5rem;
    line-height: 1;
    cursor: pointer;
  }
  .settings-close:hover {
    background: #f0f0f0;
    color: #1a1a1a;
  }
  .settings-section {
    margin-bottom: 1.25rem;
  }
  .settings-label {
    font-size: 0.85rem;
    color: #666;
    margin-bottom: 0.5rem;
  }
  .settings-check,
  .settings-radio {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.9rem;
    color: #333;
    cursor: pointer;
    margin-bottom: 0.35rem;
  }
  .settings-check input,
  .settings-radio input {
    margin: 0;
  }
  .settings-section-llm {
    padding-top: 0.5rem;
    border-top: 1px solid #eee;
  }
  .settings-field {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    margin-bottom: 0.75rem;
    font-size: 0.9rem;
  }
  .settings-field-label {
    color: #666;
  }
  .settings-input {
    padding: 0.4rem 0.6rem;
    border: 1px solid #ccc;
    border-radius: 6px;
    font-size: 0.85rem;
    font-family: inherit;
  }
  .settings-input::placeholder {
    color: #999;
  }
  .settings-llm-btn {
    width: 100%;
    margin-top: 0.25rem;
  }
  .settings-btn {
    width: 100%;
    margin-top: 1rem;
  }
  .input {
    flex: 1;
    min-width: 180px;
    padding: 0.6rem 1rem;
    border: 1px solid #ccc;
    border-radius: 6px;
    background: #fff;
    color: #1a1a1a;
    font-size: 1rem;
    font-family: inherit;
  }
  .input::placeholder {
    color: #999;
  }
  .input:focus {
    outline: none;
    border-color: #333;
  }
  .btn {
    padding: 0.6rem 1.2rem;
    border: 1px solid #333;
    border-radius: 6px;
    font-size: 0.95rem;
    font-family: inherit;
    cursor: pointer;
    background: #fff;
    color: #1a1a1a;
    transition: background 0.2s, color 0.2s;
  }
  .btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
  .btn-primary {
    background: #1a1a1a;
    color: #fff;
    border-color: #1a1a1a;
  }
  .btn-primary:hover:not(:disabled) {
    background: #333;
  }
  .btn-secondary:hover:not(:disabled) {
    background: #f0f0f0;
  }
  .error {
    color: #b33;
    margin: 1rem 0 0;
    font-size: 0.9rem;
  }
  .graph-container {
    width: 100%;
    flex: 1;
    min-height: 0;
    background: #fff;
    border-radius: 8px;
    border: 1px solid #e0e0e0;
    overflow: hidden;
  }
  .graph-container :deep(svg) {
    display: block;
  }
  .graph-container :deep(circle) {
    cursor: grab;
  }
  .graph-container :deep(circle:active) {
    cursor: grabbing;
  }
  .node-tooltip {
    position: fixed;
    z-index: 100;
    margin: 10px 0 0 10px;
    padding: 8px 12px;
    max-width: 280px;
    background: #1a1a1a;
    color: #fff;
    border-radius: 6px;
    font-size: 13px;
    line-height: 1.4;
    box-shadow: 0 2px 12px rgba(0,0,0,0.2);
    pointer-events: none;
  }
  .node-tooltip-word {
    font-weight: 600;
    display: block;
    margin-bottom: 2px;
  }
  .node-tooltip-definition {
    display: block;
    font-size: 12px;
    color: #e0e0e0;
  }
</style>
