<template>
  <div class="cmd-poc" :style="{ '--role-color': role.color }">
    <!-- 顶部导航 -->
    <PocNavbar />

    <div class="cmd-body" :class="{ 'sidebar-collapsed': sidebarCollapsed }">
      <!-- 左侧角色菜单 -->
      <PocSidebar v-show="!sidebarCollapsed" />

      <!-- 主内容区 -->
      <main class="cmd-main">
        <div class="crumb-wrap">
          <el-tooltip content="隐藏/显示菜单" effect="dark" placement="bottom">
            <div class="hamburger-shell" @click="toggleSidebar">
              <hamburger :is-active="!sidebarCollapsed" class="hamburger-container" />
            </div>
          </el-tooltip>
          <el-breadcrumb class="crumb" separator="/">
            <el-breadcrumb-item>CMD POC</el-breadcrumb-item>
            <!-- 二级菜单子页：先显示父菜单（客户管理），末级用菜单名，避免与页面大标题重复 -->
            <el-breadcrumb-item v-if="currentParentMenu">{{ currentParentMenu.label }}</el-breadcrumb-item>
            <el-breadcrumb-item v-if="currentSub">{{ currentSubLabel }}</el-breadcrumb-item>
            <el-breadcrumb-item>{{ currentParentMenu ? pageTitle : pageHeadTitle }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>

        <!-- 页面标题：位于多标签栏上方 -->
        <div class="page-title">
          <div class="page-title-text">
            <h2>{{ pageHeadTitle }}</h2>
            <p>{{ pageSub }}</p>
          </div>
          <div v-if="currentPage === 'dash' && (roleKey === 'bu' || roleKey === 'gc')" class="page-title-actions">
            <el-button type="primary" plain @click="goMenu('approval')">
              {{ roleKey === 'gc' ? '进入待我决策' : '进入待我审批' }}
            </el-button>
          </div>
          <!--
            已生效主档 = 总设计「02 · 客户管理」：查询 + 主档详情 + 只读控制，不挂写入口。
            新建客户与 OCR 属于「03 · 新建客户与 OCR」场景，统一收在「处理中申请」页，
            避免同一动作在两个页重复出现、也避免主档页出现"发起"类按钮造成语义错位。
          -->
          <div v-else-if="currentPage === 'customers' && roleKey === 'business'" class="page-title-actions">
            <span class="page-title-readonly">新建客户与 OCR 识别请在「处理中申请」页发起</span>
          </div>
          <!--
            处理中申请 = 申请台账，同时是「03 · 新建客户与 OCR」的场景入口：
            OCR 与新建客户同源（新建客户弹窗内也提供「上传并OCR识别」并回填），
            故两个入口放在同一页；提交成功后会停在本页（新申请落在列表首行）。
          -->
          <div v-else-if="currentPage === 'custapps' && roleKey === 'business'" class="page-title-actions">
            <el-button plain @click="openDialog('ocr')">查看OCR识别结果</el-button>
            <el-button type="primary" plain icon="Plus" @click="openDialog('newCustomer')">新建客户</el-button>
          </div>
          <!-- 非 Business User 的客户页：不给写入口，用一行小字说明权限边界（测试报告 BUG-4） -->
          <div v-else-if="currentPage === 'customers' && !readOnly" class="page-title-actions">
            <span class="page-title-readonly">Steward 角色：新建客户由 Business User 发起，此处仅可查询与治理</span>
          </div>
          <!-- 新建导入任务是 Business User 的写操作；Steward 在批量治理页只做治理与裁决 -->
          <div v-else-if="currentPage === 'batch' && (roleKey === 'business' || roleKey === 'bu')" class="page-title-actions">
            <el-button plain @click="openDialog('template')">下载模板</el-button>
            <el-button type="primary" plain icon="Plus" @click="openDialog('batchUpload')">新建导入任务</el-button>
          </div>
          <div v-else-if="currentPage === 'hier' && !readOnly" class="page-title-actions">
            <el-button
              v-if="roleKey === 'business'"
              type="primary"
              plain
              icon="Plus"
              @click="openDialog('hierAdd', { mode: 'request' })"
            >
              发起层级关系申请
            </el-button>
            <el-button
              v-else
              type="primary"
              plain
              icon="Plus"
              @click="openDialog('hierAdd', { mode: 'manage' })"
            >
              新增层级关系
            </el-button>
          </div>
          <div v-else-if="currentPage === 'change'" class="page-title-actions">
            <el-button plain @click="openDialog('changeRequest')">发起属性变更</el-button>
            <el-button class="poc-btn-orange" plain @click="openDialog('deactivate')">申请逻辑停用</el-button>
          </div>
          <div v-else-if="currentPage === 'admin'" class="page-title-actions">
            <!-- 打开「字段与值集管理」弹窗并落到「模型版本」页签，发布动作由用户在版本列表中确认执行 -->
            <el-button type="primary" plain icon="Promotion" @click="openDialog('fields', { tab: 'version' })">发布配置版本</el-button>
          </div>
        </div>

        <!-- 标签导航：位于页面标题下方 -->
        <PocTagsView @refresh="refreshPanel" />

        <!-- 页面面板：按当前角色菜单动态渲染 -->
        <component :is="currentPanel" :key="`${currentPage}-${panelRefreshTick}`" v-bind="panelProps" />
      </main>
    </div>

    <!-- 全局弹窗宿主 -->
    <DialogHost />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, type Component } from 'vue';
import type { PageId, RoleKey } from '@/api/demo/cmdPoc/types';
import { createCmdPoc } from './composables/useCmdPoc';
import { DASHBOARD_TITLES } from './constants/roles';
import { PAGE_META } from './constants/pages';
import PocNavbar from './components/PocNavbar.vue';
import PocSidebar from './components/PocSidebar.vue';
import DialogHost from './components/DialogHost.vue';
import PocTagsView from './components/PocTagsView.vue';
import Hamburger from '@/components/Hamburger/index.vue';

// 页面面板
import DashPanel from './components/panels/DashPanel.vue';
import CustomersPanel from './components/panels/CustomersPanel.vue';
import BatchPanel from './components/panels/BatchPanel.vue';
import GovernancePanel from './components/panels/GovernancePanel.vue';
import HierarchyPanel from './components/panels/HierarchyPanel.vue';
import ChangePanel from './components/panels/ChangePanel.vue';
import ApprovalPanel from './components/panels/ApprovalPanel.vue';
import OneIdPanel from './components/panels/OneIdPanel.vue';
import DqScorePanel from './components/panels/DqScorePanel.vue';
import IntegrationPanel from './components/panels/IntegrationPanel.vue';
import AdminPanel from './components/panels/AdminPanel.vue';
import AuditPanel from './components/panels/AuditPanel.vue';
import CoveragePanel from './components/panels/CoveragePanel.vue';
import WorkflowDefinitionPanel from './components/panels/WorkflowDefinitionPanel.vue';
import FlowWorkitemPanel from './components/panels/FlowWorkitemPanel.vue';
import FlowDonePanel from './components/panels/FlowDonePanel.vue';

defineOptions({ name: 'CmdPoc' });

const props = defineProps<{ defaultRole?: RoleKey }>();

const { role, roleKey, currentPage, currentSub, currentMenu, currentParentMenu, pageTitle, readOnly, openDialog, goMenu, sidebarCollapsed, toggleSidebar, loadCustomers, loadMetadataFields } = createCmdPoc(
  (props.defaultRole ?? 'business') as RoleKey
);

/** 页面面板注册表 */
const PANEL_MAP: Record<PageId, Component> = {
  dash: DashPanel,
  customers: CustomersPanel,
  /** 与 customers 同一个面板：靠 panelProps 传入初始视图（处理中申请），不另写一份列表代码 */
  custapps: CustomersPanel,
  batch: BatchPanel,
  gov: GovernancePanel,
  hier: HierarchyPanel,
  change: ChangePanel,
  approval: ApprovalPanel,
  oneid: OneIdPanel,
  dqscore: DqScorePanel,
  integration: IntegrationPanel,
  admin: AdminPanel,
  audit: AuditPanel,
  coverage: CoveragePanel,
  flowDefinition: WorkflowDefinitionPanel,
  flowWorkitem: FlowWorkitemPanel,
  flowDone: FlowDonePanel
};

const currentPanel = computed(() => PANEL_MAP[currentPage.value] ?? DashPanel);

/**
 * 面板入参：CustomersPanel 承载两个菜单页，用页面 id 决定初始视图。
 * 切换菜单（而不是页内 tab）时，`component` 的 key 变化会重建面板，视图随之切换。
 */
const panelProps = computed(() => (currentPage.value === 'custapps' ? { defaultView: 'inFlight' as const } : {}));

/** 标签栏刷新当前面板计数 */
const panelRefreshTick = ref(0);
const refreshPanel = () => {
  panelRefreshTick.value += 1;
};

/** 工作台标题按角色区分，其余页面取固定标题或菜单名（One ID / DQ Scorecard 无菜单项，取固定标题） */
const pageHeadTitle = computed(() => {
  if (currentPage.value === 'dash') return DASHBOARD_TITLES[roleKey.value];
  return PAGE_META[currentPage.value]?.title || pageTitle.value;
});

const DASH_SUB: Record<RoleKey, string> = {
  business: '根据角色与Scope动态显示',
  bu: '本BU申请初审，异常治理与SLA管理',
  gc: '跨BU证据核对，One ID决策与重大治理',
  admin: '根据角色与Scope动态显示',
  audit: '根据角色与Scope动态显示'
};

const pageSub = computed(() => {
  if (currentPage.value === 'dash') return DASH_SUB[roleKey.value];
  if (currentPage.value === 'approval') {
    return roleKey.value === 'gc'
      ? '跨BU审批、匹配合并、One ID与重大治理任务统一处理'
      : '本BU审批、DQ复核、疑似重复、层级与批量治理统一处理';
  }
  return PAGE_META[currentPage.value]?.sub ?? '';
});

/** 下钻场景的面包屑上级名称（客户下钻 / 平台管理能力页下钻） */
const currentSubLabel = computed(() => {
  if (currentSub.value === 'customers') return currentMenu.value?.label ?? '客户管理';
  if (currentSub.value === 'admin') return PAGE_META.admin?.title ?? '平台管理';
  return '';
});

onMounted(() => {
  loadCustomers();
  loadMetadataFields();
});
</script>

<style lang="scss">
@use './styles/cmd-poc.scss';
</style>
