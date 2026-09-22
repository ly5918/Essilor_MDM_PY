<template>
  <section class="page">
    <!-- 平台固定 / 可配置口径说明（对齐 V6.1 第 16 页 Workflow配置 + 设计边界） -->
    <el-alert class="m-b-12" type="info" :closable="false" show-icon>
      <template #title>
        场景编码、流程编码与主干 BU 初审为<b>平台固定项</b>（与 SpiffWorkflow 流程定义、引擎节点定位绑定）；
        路由条件、节点路由规则、SLA、超时升级与邮件通知按场景<b>可配置</b>。
      </template>
    </el-alert>

    <el-card class="page-card" shadow="never" :body-style="{ padding: '10px 16px 14px' }">
      <div class="wd-toolbar card-toolbar">
        <div class="wd-toolbar-left">
          <span class="wd-title">工作流定义</span>
          <span class="wd-count">共 {{ scenes.length }} 条 CMD 业务工作流</span>
          <el-tag v-if="scenes.length > 0 && deployedCount === scenes.length" type="success" size="small">全部已部署</el-tag>
          <el-tag v-else-if="scenes.length > 0" type="warning" size="small">{{ deployedCount }}/{{ scenes.length }} 已部署</el-tag>
        </div>
        <div class="wd-toolbar-right">
          <el-input v-model="sceneKeyword" placeholder="场景名称 / 流程编码" clearable style="width: 220px" @keyup.enter="loadScenes" />
          <el-button type="primary" plain icon="Refresh" @click="loadScenes">刷新</el-button>
        </div>
      </div>

      <el-table v-loading="sceneLoading" border :data="visibleScenes" class="data-table">
        <el-table-column label="场景编码" prop="sceneCode" width="150" />
        <el-table-column label="业务场景（V6.1）" prop="sceneName" min-width="150" show-overflow-tooltip />
        <el-table-column label="SpiffWorkflow 流程名称" prop="flowName" min-width="150" show-overflow-tooltip />
        <el-table-column label="流程编码" prop="flowCode" min-width="165" show-overflow-tooltip />
        <el-table-column label="SLA" width="80" align="center">
          <template #default="{ row }">{{ row.slaHours ?? '—' }}h</template>
        </el-table-column>
        <el-table-column label="版本" width="80" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.version" size="small" effect="plain">{{ row.version }}</el-tag>
            <span v-else>—</span>
          </template>
        </el-table-column>
        <el-table-column label="泳道节点" prop="nodeCount" width="85" align="center" />
        <el-table-column label="部署状态" width="100" align="center">
          <template #default="{ row }">
            <el-tooltip v-if="row.deployed && row.deployedAt" :content="`部署时间：${row.deployedAt}`" placement="top">
              <el-tag type="success" size="small">已部署</el-tag>
            </el-tooltip>
            <el-tag v-else-if="row.deployed" type="success" size="small">已部署</el-tag>
            <el-tag v-else type="info" size="small">未部署</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="230" align="center" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" icon="Setting" @click="onConfig(row)">配置</el-button>
            <el-button link type="primary" size="small" icon="Share" :disabled="!row.deployed" @click="onViewSceneGraph(row)">
              泳道图
            </el-button>
            <el-button link type="primary" size="small" icon="Clock" @click="onVersions(row)">版本</el-button>
            <el-button
              v-if="!row.deployed"
              link type="warning" size="small" icon="Upload" @click="onDeploy(row, false)"
            >
              部署
            </el-button>
            <el-button
              v-else
              link type="warning" size="small" icon="RefreshRight" @click="onDeploy(row, true)"
            >
              重新部署
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 版本管理弹窗：部署历史（版本号 / 定义ID / 节点数 / 部署人 / 时间 / 当前版本标记） -->
      <el-dialog v-model="versionsOpen" :title="`版本管理 · ${versionsScene?.sceneName ?? ''}（${versionsScene?.sceneCode ?? ''}）`" width="720px">
        <el-table v-loading="versionsLoading" border :data="versions">
          <el-table-column label="版本号" width="90" align="center">
            <template #default="{ row }">
              <el-tag v-if="row.status === '0'" type="success" size="small">{{ row.versionNo }}</el-tag>
              <span v-else>{{ row.versionNo }}</span>
            </template>
          </el-table-column>
          <el-table-column label="定义 ID" prop="definitionId" min-width="180" show-overflow-tooltip />
          <el-table-column label="节点数" prop="nodeCount" width="75" align="center" />
          <el-table-column label="部署人" prop="deployedBy" width="90" align="center" />
          <el-table-column label="部署时间" width="160" align="center">
            <template #default="{ row }">{{ (row.deployedAt ?? '').replace('T', ' ').slice(0, 19) || '—' }}</template>
          </el-table-column>
          <el-table-column label="状态" width="90" align="center">
            <template #default="{ row }">
              <el-tag v-if="row.status === '0'" type="success" size="small" effect="plain">当前版本</el-tag>
              <el-tag v-else type="info" size="small" effect="plain">历史</el-tag>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-if="!versionsLoading && versions.length === 0" description="尚未部署：点击列表「部署」登记首个版本" :image-size="70" />
      </el-dialog>
    </el-card>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { ElMessage } from 'element-plus';
import { deployFlowScene, listFlowScenes, listFlowSceneVersions } from '@/api/demo/cmdPoc';
import type { FlowSceneVO, FlowSceneVersionVO } from '@/api/demo/cmdPoc/types';
import { useCmdPoc } from '../../composables/useCmdPoc';

/**
 * Platform Admin › 平台管理 › Workflow「管理」进入的工作流定义页。
 *
 * 展示 CMD 业务场景 ↔ SpiffWorkflow 流程定义映射（含 SLA / 版本 / 泳道节点数），
 * 每行可「配置」（场景级工作流配置弹窗）、「泳道图」（图形化流程蓝图）与「部署」（未部署时）。
 * 页面顶部固定一条口径说明：哪些是平台固定项、哪些按场景可配置。
 */
defineOptions({ name: 'CmdPocWorkflowDefinitionPanel' });

const { openDialog } = useCmdPoc();

const sceneLoading = ref(false);
const scenes = ref<FlowSceneVO[]>([]);
const sceneKeyword = ref('');

const deployedCount = computed(() => scenes.value.filter(s => s.deployed).length);

const visibleScenes = computed(() => {
  const kw = sceneKeyword.value.trim().toLowerCase();
  if (!kw) return scenes.value;
  return scenes.value.filter(
    s =>
      s.sceneName?.toLowerCase().includes(kw) ||
      s.flowCode?.toLowerCase().includes(kw) ||
      s.sceneCode.toLowerCase().includes(kw)
  );
});

const loadScenes = async () => {
  sceneLoading.value = true;
  try {
    scenes.value = await listFlowScenes();
  } finally {
    sceneLoading.value = false;
  }
};

/** 按场景配置：流程设计 / 路由条件 / SLA（对齐原型 Workflow配置 弹窗） */
const onConfig = (row: unknown) => {
  const scene = row as FlowSceneVO;
  openDialog('workflow', { sceneCode: scene.sceneCode, sceneName: scene.sceneName, flowCode: scene.flowCode });
};

/** 查看蓝图：定义视图（节点全部待执行） */
const onViewSceneGraph = (row: unknown) => {
  const scene = row as FlowSceneVO;
  if (!scene.deployed) {
    ElMessage.warning('该流程尚未部署到 SpiffWorkflow，请先点击「部署」');
    return;
  }
  openDialog('flowGraph', { sceneCode: scene.sceneCode, sceneName: scene.sceneName, flowCode: scene.flowCode });
};

/** 部署单个场景到 SpiffWorkflow（幂等：BPMN 变更时版本进位，否则提示复用当前版本） */
const onDeploy = async (row: unknown, redeploy: boolean) => {
  const scene = row as FlowSceneVO;
  sceneLoading.value = true;
  try {
    const result = await deployFlowScene(scene.sceneCode);
    if (redeploy && !result.created) {
      ElMessage.info(`流程「${scene.sceneName}」已是最新版本 ${result.versionNo}（BPMN 未变化）`);
    } else {
      ElMessage.success(`流程「${scene.sceneName}」已部署为 ${result.versionNo}`);
    }
    await loadScenes();
  } catch {
    ElMessage.error('部署失败，请检查后端日志');
  } finally {
    sceneLoading.value = false;
  }
};

/** 版本管理弹窗：展示该场景的部署 / 版本历史 */
const versionsOpen = ref(false);
const versionsLoading = ref(false);
const versionsScene = ref<FlowSceneVO | null>(null);
const versions = ref<FlowSceneVersionVO[]>([]);
const onVersions = async (row: unknown) => {
  const scene = row as FlowSceneVO;
  versionsScene.value = scene;
  versionsOpen.value = true;
  versionsLoading.value = true;
  try {
    versions.value = await listFlowSceneVersions(scene.sceneCode);
  } finally {
    versionsLoading.value = false;
  }
};

onMounted(loadScenes);
</script>

<style scoped lang="scss">
.wd-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;

  &-left {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  &-right {
    display: flex;
    align-items: center;
    gap: 8px;
  }
}

.wd-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.wd-count {
  font-size: 13px;
  color: var(--el-text-color-secondary);
}
</style>
