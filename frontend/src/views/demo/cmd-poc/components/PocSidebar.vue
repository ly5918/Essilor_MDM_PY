<template>
  <aside class="sidebar">
    <!-- 左侧栏：角色信息 + 角色动态菜单 -->
    <div class="side-user">
      <div class="side-avatar" :style="{ background: role.color }">{{ role.alias }}</div>
      <div class="side-name">{{ role.name }}</div>
      <div class="side-scope">{{ role.scope }}</div>
    </div>

    <div class="nav-title">ROLE-BASED NAVIGATION</div>

    <el-menu
      class="side-menu"
      :default-active="currentPage"
      background-color="transparent"
      text-color="#C7D2DC"
      active-text-color="#FFFFFF"
      :default-openeds="defaultOpeneds"
      @select="onSelect"
    >
      <template v-for="menu in role.menus" :key="menu.id">
        <!-- RuoYi 二级菜单：有子菜单时渲染可展开的父菜单 -->
        <el-sub-menu v-if="menu.children?.length" :index="menu.id">
          <template #title>
            <span class="cn-ico">{{ menu.icon }}</span>
            <span class="cn-txt">{{ menu.label }}</span>
          </template>
          <el-menu-item v-for="child in menu.children" :key="child.id" :index="child.id" class="side-sub-item">
            <span class="cn-ico cn-ico-sub">{{ child.icon }}</span>
            <span class="cn-txt">{{ child.label }}</span>
            <span v-if="navCount(child)" class="cn-badge">{{ navCount(child) }}</span>
          </el-menu-item>
        </el-sub-menu>
        <el-menu-item v-else :index="menu.id">
          <span class="cn-ico">{{ menu.icon }}</span>
          <span class="cn-txt">{{ menu.label }}</span>
          <span v-if="navCount(menu)" class="cn-badge">{{ navCount(menu) }}</span>
        </el-menu-item>
      </template>
    </el-menu>
  </aside>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import type { PageId } from '@/api/demo/cmdPoc/types';
import { getCustomerStats, getNavBadges } from '@/api/demo/cmdPoc';
import type { PocMenu } from '../constants/roles';
import { useCmdPoc } from '../composables/useCmdPoc';

const { role, roleKey, currentPage, goMenu, badgeVersion } = useCmdPoc();

/**
 * 菜单「数据统计」角标：**仅审批类菜单**显示待处理条数，不是每个菜单都要统计。
 *
 * 口径：只有需要人工审批 / 复核的菜单才挂角标，由 roles.ts 的 `requiresApproval` 声明
 * （当前 = BU Scope「治理与审批」「批量治理」、GC Scope「全局治理决策」「批量治理」）。
 * 数字由后端按业务表实时聚合，key = 菜单 id，口径与点进页面后的数字一致。
 *
 * 角色若没有任何审批类菜单（Business User / Platform Admin / Auditor），直接跳过请求，
 * 避免无谓查询，也保证这些角色菜单上不会冒出数字。
 */
const navBadges = ref<Record<string, number>>({});

/** 当前角色是否存在需要显示待办的审批类菜单 */
const hasApprovalMenu = computed(() => {
  const walk = (menus: typeof role.value.menus): boolean =>
    menus.some(m => m.requiresApproval || (m.children?.length ? walk(m.children) : false));
  return walk(role.value.menus);
});

const fetchBadges = async () => {
  if (!hasApprovalMenu.value) {
    navBadges.value = {};
    return;
  }
  try {
    navBadges.value = await getNavBadges(roleKey.value);
  } catch {
    /* 拉取失败时保留上一次数字，避免菜单角标莫名消失 */
  }
};

/** 菜单项 badge 映射（模板侧再叠加 requiresApproval 判断；值为 0 时不显示角标） */
const badgeMap = computed<Record<string, number>>(() => navBadges.value);

/**
 * 「处理中申请」在途条数角标（roles.ts 里 `badge: 'inFlight'` 的菜单）。
 *
 * 与审批类角标分开取数：审批待办是「别人提交、等我来审」（只有 Steward 有），
 * 在途申请是「我提交的、还在流程里」（业务用户 / 审计角色同样要看），
 * 二者口径与数据源都不同，因此不复用 /cmd/nav/badge。数字取自
 * /cmd/customer/stats 的 pendingCount —— 后端口径就是申请单表 status ∈ (pending, returned)，
 * 与「处理中申请」列表的「在途」一致（/application/stats 目前只回 total/pending/approved/rejected，
 * 没有 inFlight，用它会把角标恒算成 0）。
 */
const appInFlight = ref(0);

/** 当前角色是否存在需要展示在途数的菜单（Business / Steward / Auditor 都有） */
const hasInFlightMenu = computed(() => {
  const walk = (menus: typeof role.value.menus): boolean =>
    menus.some(m => m.badge === 'inFlight' || (m.children?.length ? walk(m.children) : false));
  return walk(role.value.menus);
});

const fetchAppInFlight = async () => {
  if (!hasInFlightMenu.value) {
    appInFlight.value = 0;
    return;
  }
  try {
    appInFlight.value = (await getCustomerStats()).pendingCount ?? 0;
  } catch {
    /* 拉取失败时保留上一次数字，避免角标莫名消失；失败不该把「有在途」显示成「没有」 */
  }
};

/**
 * 菜单角标取值：按 roles.ts 声明的 `badge` 来源取数，0 / 未声明则不渲染。
 * （approval 类菜单仍由 requiresApproval + /cmd/nav/badge 驱动，行为不变）
 */
const navCount = (menu: PocMenu): number =>
  menu.badge === 'inFlight' ? appInFlight.value : (badgeMap.value[menu.id] ?? 0);

/** 切换角色时按新角色重新统计（BU / GC / Admin / Auditor 口径不同） */
watch(roleKey, () => {
  fetchBadges();
  fetchAppInFlight();
});

/** 审批/提交等操作后刷新 badge（badgeVersion 自增触发） */
watch(badgeVersion, () => {
  fetchBadges();
  fetchAppInFlight();
});

onMounted(() => {
  fetchBadges();
  fetchAppInFlight();
});

/** 默认展开包含当前页面的父菜单（RuoYi 行为：进入子页面时父菜单保持展开） */
const defaultOpeneds = computed(() =>
  role.value.menus.filter(menu => menu.children?.some(child => child.id === currentPage.value)).map(menu => menu.id)
);

const onSelect = (index: string) => goMenu(index as PageId);
</script>
