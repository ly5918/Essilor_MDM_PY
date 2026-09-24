<template>
  <section class="page">
    <!-- KPI 概览：待我处理 / 临近SLA / 已超时 / 退回待补充 / 本周已处理 -->
    <div class="ap-kpis">
      <div v-for="kpi in kpis" :key="kpi.label" class="ap-kpi">
        <b>{{ kpi.value }}</b>
        <span>{{ kpi.label }}</span>
      </div>
    </div>

    <!-- Tab：全部待办 / 审批任务 / 治理复核 / 升级与退回 / 我已处理 -->
    <el-card class="page-card" shadow="never" :body-style="{ padding: '12px 16px' }">
      <el-tabs v-model="activeTab" class="ap-tabs" @tab-change="onTabChange">
        <el-tab-pane v-for="tab in TABS" :key="tab.key" :name="tab.key">
          <template #label>{{ tab.label }}</template>
        </el-tab-pane>
      </el-tabs>

      <!-- 统一筛选条 -->
      <div class="ap-filter card-toolbar">
        <el-select v-model="filter.taskType" placeholder="全部任务类型" clearable style="width: 160px">
          <el-option v-for="t in TASK_TYPE_OPTIONS" :key="t" :label="t" :value="t" />
        </el-select>
        <el-select v-model="filter.bu" placeholder="全部BU" clearable style="width: 140px">
          <el-option v-for="b in BU_OPTIONS" :key="b" :label="b" :value="b" />
        </el-select>
        <el-select v-model="filter.sla" placeholder="全部SLA" clearable style="width: 130px">
          <el-option label="临近SLA" value="near" />
          <el-option label="已超时" value="over" />
        </el-select>
        <el-select v-model="filter.risk" placeholder="全部风险" clearable style="width: 120px">
          <el-option label="High" value="High" />
          <el-option label="Medium" value="Medium" />
        </el-select>
        <el-input v-model="filter.keyword" placeholder="One ID / 申请编号 / 客户名称" clearable style="width: 240px" @keyup.enter="applyFilter" />
        <el-button type="primary" plain icon="Search" @click="applyFilter">查询</el-button>
      </div>

      <!-- 队列取数失败（502 / 后端重启）必须显性化：否则「暂无数据」会被读成「没有待办」 -->
      <LoadErrorBar :message="loadError" @retry="loadData" />

      <!-- 左列表 + 右侧只读速览：点行看概要，「进入审批」打开宽弹窗完成审批操作 -->
      <div class="ap-layout">
      <div class="ap-list">
        <div class="ap-list-title">
          {{ tabLabel }}
          <span class="ap-list-tip">点击任务行查看概要，点右侧「进入审批」办理</span>
        </div>
          <el-table
            v-loading="loading"
            ref="tableRef"
            border
            :data="visibleTasks"
            :height="tableHeight"
            class="data-table"
            highlight-current-row
            :current-row-key="selectedId"
            row-key="taskId"
            :row-style="{ cursor: 'pointer' }"
            :empty-text="loadError ? '加载失败，请点击上方「重新加载」' : loading ? '正在加载待办队列…' : '暂无数据'"
            @current-change="onRowSelect"
            @row-click="onRowSelect"
          >
            <!-- 任务编号：业务主键，固定单行显示（折行会让整表行高参差），超长时省略号 + hover 查看 -->
            <el-table-column label="任务编号" prop="taskId" width="168" show-overflow-tooltip />
            <!--
              状态列：待办页签（审批任务 / 治理复核）只含未闭环任务，但
              「全部待办」同时含「待审批」与「已退回」两类，二者处置方式不同
              （前者直接审批，后者等申请人补充材料后重新提交），必须显性区分。
            -->
            <el-table-column label="状态" width="90" align="center">
              <template #default="{ row }">
                <el-tag size="small" :type="rowStatusTag(row.status)" effect="plain">{{ rowStatusText(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <!-- One ID 列已移除：批次/合并任务该列为空易误读，One ID 统一在右侧详情头部展示 -->
            <!--
              客户/主题：同一统一社会信用代码下若还有其它「在途申请」，在名称右侧显性标注。
              为什么必须在这里提示：重复提交的两条常落在不同 Scope / 节点（一条在 BU 初审、
              一条在 GC 决策），由两个角色各自持有待办、彼此完全不可见，
              Steward 只看自己队列永远发现不了「同一家公司被建了两次号」。
            -->
            <el-table-column label="客户/主题" prop="customerName" min-width="200">
              <template #default="{ row }">
                <!-- 不用列的 show-overflow-tooltip：该列内容是多节点 flex，
                     EP 的单元格省略号只认纯文本，套上 div 会被硬裁掉且没有「…」。
                     这里自己做省略号 + 原生 title，重复标签另有悬浮提示。 -->
                <div class="ap-subject">
                  <span class="ap-subject-name" :title="row.customerName">{{ row.customerName }}</span>
                  <el-tooltip v-if="row.dupInFlight > 0" :content="row.dupPeerSummary || '同主体存在其它在途申请'" placement="top">
                    <el-tag class="ap-dup-tag" size="small" type="danger" effect="plain">同主体在途{{ row.dupInFlight }}</el-tag>
                  </el-tooltip>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="任务类型" prop="taskType" width="108" />
            <el-table-column label="来源" prop="source" width="100" />
            <el-table-column label="BU" prop="bu" width="104" />
            <el-table-column label="DQ" prop="dq" width="84" align="center" />
            <el-table-column label="Match" prop="match" width="96" align="center" />
            <el-table-column label="SLA" prop="sla" width="72" align="center" />
            <el-table-column label="风险" width="84" align="center">
              <template #default="{ row }">
                <el-tag :type="RISK_MAP[row.risk].type" size="small">{{ row.risk }}</el-tag>
              </template>
            </el-table-column>
          </el-table>

          <!-- 分页 -->
          <div class="pagination-container" v-if="total > 0">
            <el-pagination
              v-model:current-page="pageNum"
              v-model:page-size="pageSize"
              :page-sizes="[10, 20, 50, 100]"
              :total="total"
              layout="total, sizes, prev, pager, next, jumper"
              @size-change="loadData"
              @current-change="loadData"
            />
          </div>
        </div>

        <!-- 右侧速览（只读）：概要信息 + 进入审批入口；完整治理证据与审批动作在弹窗中操作 -->
        <div class="ap-detail ap-quick">
          <template v-if="detail">
            <div class="ap-detail-head">
              <h3 class="ap-detail-name">{{ detail.name }}</h3>
              <div class="ap-detail-meta">
                <div class="ap-detail-tags">
                  <!-- 状态置顶：终态任务的按钮区为空是刻意的（已办结不可再审），必须先看到状态再往下看 -->
                  <el-tag size="small" :type="rowStatusTag(detail.status)" effect="dark">{{ rowStatusText(detail.status) }}</el-tag>
                  <el-tag v-if="detail.oneId" size="small" type="success" effect="dark">One ID：{{ detail.oneId }}</el-tag>
                  <!-- 批次级审批：批量导入确认以「批次号」为全链路业务主键，One ID 在批准后按行生成 -->
                  <el-tag v-if="detail.bizId" size="small" type="info" effect="plain">批次号：{{ detail.bizId }}</el-tag>
                  <el-tag size="small" type="primary">{{ sceneText }}</el-tag>
                  <el-tag size="small" :type="isGc ? 'warning' : 'info'">{{ isGc ? 'GC Scope' : 'BU Scope' }}</el-tag>
                </div>
                <div class="ap-detail-ops">
                  <!-- 流程跟踪：泳道图步骤条 + SpiffWorkflow 实例进度（场景泳道图可视化） -->
                  <el-button link type="primary" icon="Share" @click="onOpenFlowTrace">流程跟踪</el-button>
                  <!-- MERGE 场景：疑似/精准重复任务可直接发起客户合并（总设计 MERGE 触发路径） -->
                  <el-button v-if="canMerge" link type="warning" icon="Connection" @click="onLaunchMerge">发起合并</el-button>
                </div>
              </div>
            </div>
            <div class="ap-detail-body">
              <h4>申请信息</h4>
              <div class="h-kv">
                <div>提交人</div>
                <div>{{ detail.submitter }}</div>
                <div>当前节点</div>
                <div>{{ detail.currentNode }}</div>
                <div>SLA</div>
                <div>{{ detail.sla }}</div>
              </div>

              <h4>自动检查结果</h4>
              <div class="ap-check">
                <div>
                  <b>{{ isBatch ? 'Data Quality（批次均分）' : 'Data Quality' }}</b><br />{{ detail.dq }}
                </div>
                <div>
                  <b>{{ isBatch ? 'Duplicate Check（分流结论）' : 'Duplicate Check' }}</b><br />{{ detail.duplicate }}
                </div>
              </div>

              <h4>{{ isGc ? 'GC治理决策' : 'BU初审判断' }}</h4>
              <div class="ap-decisions">
                <el-tag v-for="d in detail.decisions" :key="d" class="ap-tag" effect="plain">{{ d }}</el-tag>
              </div>
            </div>
            <div class="ap-quick-foot">
              <!--
                动作区按状态分流：未闭环任务给「进入审批」；已办结任务后端不下发任何动作，
                若还摆一个「进入审批」按钮，点进去就是空白动作区——正是「点进去没有审批按钮」
                的来源。此处改为直接说明状态 + 改走流程跟踪看处理过程。
              -->
              <template v-if="hasActions">
                <span class="ap-quick-hint">完整治理证据（字段级对比）与审批动作请在审批弹窗中查看操作</span>
                <el-button type="primary" icon="EditPen" @click="openApproval">进入审批</el-button>
              </template>
              <template v-else>
                <span class="ap-quick-hint is-closed">
                  <template v-if="(detail.status ?? '').toUpperCase() === 'RETURNED'">
                    已退回申请人修改重报：等待申请人在「客户管理 → 处理中申请」重新提交后，本单回到待办
                  </template>
                  <template v-else>
                    该任务当前状态为「{{ rowStatusText(detail.status) }}」，无可执行动作
                    <template v-if="detail.finishTime">（{{ detail.finishTime }} 办结）</template>
                  </template>
                </span>
                <!-- 已办结/已退回仍要看完整治理证据：弹窗保留为只读详情，只是动作区换成状态说明 -->
                <el-button plain icon="View" @click="openApproval">查看详情</el-button>
              </template>
            </div>
          </template>
          <el-empty v-else description="选择左侧任务查看概要" />
        </div>
      </div>

      <!-- 审批详情弹窗：宽容器（约 1040px）让证据字段对比 / DQ 明细 / 动作区完整铺开 -->
      <el-dialog v-model="detailOpen" :title="detailTitle" width="1040px" top="6vh" class="ap-dlg" destroy-on-close>
          <template v-if="detail">
            <div class="ap-detail-head">
              <h3 class="ap-detail-name">{{ detail.name }}</h3>
              <div class="ap-detail-meta">
                <div class="ap-detail-tags">
                  <!-- 状态置顶：终态任务的按钮区为空是刻意的（已办结不可再审），必须先看到状态再往下看 -->
                  <el-tag size="small" :type="rowStatusTag(detail.status)" effect="dark">{{ rowStatusText(detail.status) }}</el-tag>
                  <el-tag v-if="detail.oneId" size="small" type="success" effect="dark">One ID：{{ detail.oneId }}</el-tag>
                  <!-- 批次级审批：批量导入确认以「批次号」为全链路业务主键，One ID 在批准后按行生成 -->
                  <el-tag v-if="detail.bizId" size="small" type="info" effect="plain">批次号：{{ detail.bizId }}</el-tag>
                  <el-tag v-if="detail.bizId && !detail.oneId" size="small" type="warning" effect="plain">
                    批次级审批 · 批准后逐条生成 One ID
                  </el-tag>
                  <el-tag size="small" type="primary">{{ sceneText }}</el-tag>
                  <el-tag size="small" :type="isGc ? 'warning' : 'info'">{{ isGc ? 'GC Scope' : 'BU Scope' }}</el-tag>
                </div>
                <div class="ap-detail-ops">
                  <!-- 流程跟踪：泳道图步骤条 + SpiffWorkflow 实例进度（场景泳道图可视化） -->
                  <el-button link type="primary" icon="Share" @click="onOpenFlowTrace">流程跟踪</el-button>
                  <!-- MERGE 场景：疑似/精准重复任务可直接发起客户合并（总设计 MERGE 触发路径） -->
                  <el-button v-if="canMerge" link type="warning" icon="Connection" @click="onLaunchMerge">发起合并</el-button>
                </div>
              </div>
            </div>

            <div class="ap-detail-body">
              <h4>申请信息</h4>
              <div class="h-kv">
                <div>提交人</div>
                <div>{{ detail.submitter }}</div>
                <div>当前节点</div>
                <div>{{ detail.currentNode }}</div>
                <div>SLA</div>
                <div>{{ detail.sla }}</div>
              </div>

              <h4>自动检查结果</h4>
              <div class="ap-check">
                <div>
                  <b>{{ isBatch ? 'Data Quality（批次均分）' : 'Data Quality' }}</b><br />{{ detail.dq }}
                </div>
                <div>
                  <b>{{ isBatch ? 'Duplicate Check（分流结论）' : 'Duplicate Check' }}</b><br />{{ detail.duplicate }}
                </div>
              </div>

              <h4>{{ isGc ? 'GC治理决策' : 'BU初审判断' }}</h4>
              <div class="ap-decisions">
                <el-tag v-for="d in detail.decisions" :key="d" class="ap-tag" effect="plain">{{ d }}</el-tag>
              </div>

              <h4>治理证据</h4>
              <!-- 疑似/精准重复：字段级命中高亮对比（借鉴 DCR Matching Review）；
                   无可比数据时整块隐藏，退回下方纯文本证据列表 -->
              <div v-if="hasCompare" class="ap-cand">
                <div class="ap-cand-head">
                  <el-tag size="small" type="success" effect="dark">命中候选：{{ candOneId }}</el-tag>
                  <el-tag v-if="candCrossBu" size="small" type="danger" effect="plain">跨 BU</el-tag>
                  <span v-if="isInFlightCand" class="ap-cand-hint is-warn">
                    命中候选是<b>尚未审批完成的在途申请</b>（库里暂无该主体的已发布主档）：
                    不能「关联已有主档」，处置为撤回本单 / 确认为不同主体继续新建 / 退回修正
                  </span>
                  <span v-else class="ap-cand-hint">确认关联后，本申请将转为对该 One ID 主档的更新，不再新建客户</span>
                </div>
                <div class="ap-cmp-head">
                  <span>对比字段</span>
                  <span>新申请</span>
                  <span>命中主档</span>
                  <span class="ap-cmp-flag">匹配</span>
                </div>
                <div v-for="row in candidateCompare" :key="row.label" class="ap-cmp-row">
                  <span class="ap-cmp-label">{{ row.label }}</span>
                  <span class="ap-cmp-val" :class="`is-${row.status.toLowerCase()}`">{{ row.incoming || '（空）' }}</span>
                  <span class="ap-cmp-val" :class="`is-${row.status.toLowerCase()}`">{{ row.existing || '（空）' }}</span>
                  <span class="ap-cmp-flag">
                    <el-tag size="small" :type="cmpFlagTag(row.status)" effect="plain">{{ cmpFlagText(row.status) }}</el-tag>
                  </span>
                </div>
              </div>
              <!-- 后端以 JSON 快照下发，逐条渲染为「标签 / 值」；非 JSON 时原样展示 -->
              <div class="ap-evidence">
                <template v-if="evidenceRest.length">
                  <div v-for="row in evidenceRest" :key="row.label" class="ap-ev-row">
                    <span class="ap-ev-key">{{ row.label }}</span>
                    <span class="ap-ev-val">{{ row.value }}</span>
                  </div>
                </template>
                <span v-else>{{ detail.evidence }}</span>
              </div>

            </div>
          </template>
          <div v-else v-loading="true" class="ap-dlg-loading" element-loading-text="加载审批详情…" />

          <!--
            动作区常驻弹窗底部（sticky footer），不再跟在长内容的最末尾。
            原来「审批意见 + 动作按钮」排在治理证据之后，证据区一长就必须滚到弹窗底部
            才看得到按钮，第一眼的观感就是「点进去没有审批按钮」；审批的主操作不该藏在滚动区里。
            已办结任务后端不下发动作，这里改为状态说明 + 处理过程入口，把「为什么没有按钮」讲明白。
          -->
          <template #footer>
            <div v-if="detail" class="ap-dlg-foot">
              <template v-if="hasActions">
                <!--
                  审批意见为**必填**：未填写时下方全部审批动作按钮置灰不可点。
                  审批动作会写审批轨迹并推进流程，意见是后续追溯/审计的唯一人工说明，
                  留空则轨迹里只剩「谁点了什么」，无法还原判断依据。
                -->
                <div class="ap-foot-comment-head">
                  <span class="ap-foot-comment-label">
                    审批意见<span class="ap-req">*</span>
                  </span>
                  <span class="ap-foot-comment-hint" :class="{ 'is-ok': canSubmitAction }">
                    {{ canSubmitAction ? '已填写，可选择下方审批动作' : '必填：填写后才能执行审批动作' }}
                  </span>
                </div>
                <el-input
                  ref="commentRef"
                  v-model="comment"
                  class="ap-foot-comment"
                  type="textarea"
                  :rows="2"
                  :maxlength="500"
                  show-word-limit
                  resize="none"
                  placeholder="请输入审批意见（必填，将写入审批轨迹）"
                />
                <div class="ap-actions">
                  <el-button
                    v-for="act in detail.actions"
                    :key="act.key"
                    :type="act.type"
                    :loading="submitting"
                    :disabled="submitting || !canSubmitAction"
                    @click="onAction(act)"
                  >
                    {{ act.label }}
                  </el-button>
                </div>
              </template>
              <div v-else class="ap-foot-closed">
                <el-tag :type="rowStatusTag(detail.status)" effect="dark">{{ rowStatusText(detail.status) }}</el-tag>
                <span class="ap-foot-closed-text">
                  <template v-if="(detail.status ?? '').toUpperCase() === 'RETURNED'">
                    该单已退回申请人修改重报，审批侧暂无动作；申请人在「处理中申请」重新提交后回到待办
                  </template>
                  <template v-else>
                    该任务已办结，不再提供审批动作
                  </template>
                  <template v-if="detail.submitTime">｜提交 {{ detail.submitTime }}</template>
                  <template v-if="detail.opinion">｜意见：{{ detail.opinion }}</template>
                </span>
                <el-button plain icon="Share" @click="onOpenFlowTrace">查看处理过程</el-button>
              </div>
            </div>
          </template>
      </el-dialog>
    </el-card>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import LoadErrorBar from '../LoadErrorBar.vue';
import { describeError } from '../../composables/loadError';
import {
  BIZ_TYPE_TEXT,
  SCENE_TEXT,
  getApprovalKpis,
  getApprovalTaskDetail,
  listApprovalTasksByCategory,
  submitApprovalAction
} from '@/api/demo/cmdPoc';
import type {
  ApprovalKpiVO,
  ApprovalTaskCategory,
  ApprovalTaskDetailVO,
  ApprovalTaskVO,
  DuplicateFieldStatus,
  RoleKey
} from '@/api/demo/cmdPoc/types';
import { useCmdPoc } from '../../composables/useCmdPoc';
import { useListTableHeight } from '../../composables/useListTableHeight';

defineOptions({ name: 'CmdPocApprovalPanel' });

/** 表格高度自适应 + 分页固定在内容区底部（与其他列表面板一致，reserve=分页条+卡片内边距） */
const { tableRef, tableHeight, recalc } = useListTableHeight(70);

const { roleKey, openDialog, refreshBadge } = useCmdPoc();
/** 仅 BU / GC 拥有审批菜单；其余角色理论上不会进入本面板 */
const isGc = computed(() => roleKey.value === 'gc');
const scope = computed<'bu' | 'gc'>(() => (isGc.value ? 'gc' : 'bu'));

const RISK_MAP: Record<string, { type: 'danger' | 'warning' | 'info' }> = {
  High: { type: 'danger' },
  Medium: { type: 'warning' },
  Low: { type: 'info' }
};

/**
 * 任务状态 → 展示文案 / 标签色
 *
 * 为什么列表与详情都必须显性展示状态：
 * 「全部待办」同时含待审批（PENDING）与已退回（RETURNED）两类未闭环任务，
 * 而「审批任务 / 治理复核」页签只按建表分类取未闭环，不显示状态时用户无法解释
 * 为什么同一条数据在不同页签下的条数不一样；已办结（APPROVED / COMPLETED /
 * REJECTED / CANCELLED）的任务动作按钮为空是**设计如此**（不能二次审批），
 * 必须靠状态说明，而不是给一个空白动作区让人猜。
 */
const STATUS_MAP: Record<string, { text: string; type: 'primary' | 'success' | 'warning' | 'danger' | 'info' }> = {
  DRAFT: { text: '草稿', type: 'info' },
  PENDING: { text: '待审批', type: 'warning' },
  ESCALATED: { text: '已升级', type: 'warning' },
  RETURNED: { text: '已退回', type: 'danger' },
  APPROVED: { text: '已批准', type: 'success' },
  COMPLETED: { text: '已办结', type: 'success' },
  REJECTED: { text: '已拒绝', type: 'info' },
  CANCELLED: { text: '已取消', type: 'info' }
};
const rowStatusText = (status?: string) => STATUS_MAP[(status ?? '').toUpperCase()]?.text ?? (status || '—');
const rowStatusTag = (status?: string) => STATUS_MAP[(status ?? '').toUpperCase()]?.type ?? 'info';

/**
 * 页签 → 后端队列分类
 *
 * 每个页签各查各的分类，前端不再按中文 taskType 文本做业务过滤：
 * 之前「全部待办」取的是三类合并后再 slice(pageSize) 的结果，审批类一满页就会
 * 把治理复核 / 退回任务截断，且新增业务类型时任务会静默消失。
 */
const TABS = [
  { key: 'all', label: '全部待办', category: 'ALL' },
  { key: 'approval', label: '审批任务', category: 'APPROVAL' },
  { key: 'governance', label: '治理复核', category: 'GOVERNANCE' },
  { key: 'returned', label: '升级与退回', category: 'RETURNED' },
  { key: 'done', label: '我已处理', category: 'DONE' }
] as const;

const TASK_TYPE_OPTIONS = ['客户新建', '客户变更', '逻辑停用', '层级关系', '疑似重复', '客户合并', 'DQ异常', '批量治理', '批量导入确认'];
const BU_OPTIONS = ['High End', 'Mainstream', 'Cross-BU'];

/**
 * 任务类型筛选项（页面筛选条下拉）
 *
 * 后端 bizType 实际值：客户新建 / 客户新建 - OCR（单条创建，含 OCR 来源）、
 * 层级关系、客户合并（MERGE，按 cross_bu_flag 如实展示，跨BU单显示「跨BU合并」）、
 * 批量导入确认（IMPORT）等。本列表 taskType 统一走 BIZ_TYPE_TEXT 映射 → 「客户合并」，
 * 故筛选项不再保留旧的「跨BU合并」（选了会匹配不到任何行）。
 */

const kpis = ref<ApprovalKpiVO[]>([]);
/** 当前页签的任务（服务端分页，与该页签的 total 严格一致） */
const allTasks = ref<ApprovalTaskVO[]>([]);
/** 首屏即置 loading：避免第一帧渲染出「暂无数据」被读成「没有数据」（复测报告：渲染时序） */
const loading = ref(true);
const activeTab = ref<(typeof TABS)[number]['key']>('all');
const detailOpen = ref(false);
const selectedId = ref('');
const selectedRow = ref<ApprovalTaskVO | null>(null);
/** 正在取详情的任务号：current-change 与 row-click 可能对同一次点击双触发，用它防重入 */
const loadingDetailId = ref('');
const detail = ref<ApprovalTaskDetailVO | null>(null);
/** 队列请求失败原因：非空时显性提示并可重试，避免 502 被读成「没有待办」（复测报告 BUG-01 观感来源） */
const loadError = ref('');
const comment = ref('');
/** 审批意见输入框实例：未填写却触发动作时把焦点自动拉回输入框 */
const commentRef = ref<{ focus?: () => void } | null>(null);
const submitting = ref(false);
const pageNum = ref(1);
const pageSize = ref(10);
const total = ref(0);

const filter = reactive({ taskType: '', bu: '', sla: '', risk: '', keyword: '' });

const tabLabel = computed(() => TABS.find(t => t.key === activeTab.value)?.label ?? '全部待办');

/** 当前页签对应的后端队列分类（页签与后端口径严格一致，前端不再做业务过滤） */
const activeCategory = computed<ApprovalTaskCategory>(
  () => (TABS.find(t => t.key === activeTab.value)?.category ?? 'ALL') as ApprovalTaskCategory
);

/**
 * 是否为批量导入确认（批次级审批）
 *
 * 总设计场景二「批量导入」：BU Scope 治理处理 Same-BU 候选（批量关联 / 排除 / 退回修复），
 * 批量处理结果节点才「Exact 关联已有 One ID；New 审批后生成 One ID」——即**一条导入任务
 * 对应一条审批待办**，逐条粒度体现在对批次内各行的治理决策，而不是把一批拆成 N 条审批。
 * 后端对该场景存业务码 IMPORT，此处按业务码识别，不改动后端语义。
 */
const isBatch = computed(() => detail.value?.scene === 'IMPORT');

/**
 * 疑似/精准重复任务可发起客户合并（SUSPECTED → 跨BU治理；EXACT → 关联确认）。
 *
 * 但**在途申请命中**不算：命中的是另一条尚未审批完成的申请，库里没有该主体的
 * 已发布主档，「发起合并」的语义（并入已有 One ID）不成立，必须隐藏——
 * 否则又回到「关联已有主档」的老路，与总设计在途处置（撤回 / 不同主体继续新建 / 退回）相悖。
 * isInFlightCand 与后端 _is_in_flight_duplicate 同源判定（证据含「在途申请=是」或「命中来源=在途」）。
 */
const canMerge = computed(() => {
  const d = detail.value;
  return !!d?.oneId
    && /SUSPECTED|EXACT|疑似|重复/i.test(d.duplicate ?? '')
    && !isInFlightCand.value;
});

/**
 * 当前任务是否仍有可执行动作。
 *
 * 终态任务（已批准 / 已拒绝 / 已办结 / 已取消）后端**按设计**不下发动作按钮——
 * 已办结的业务不能再被二次审批。因此动作区必须按此分支渲染：
 * 有动作 → 审批意见 + 动作按钮；无动作 → 状态说明，而不是一个空白区域。
 */
const hasActions = computed(() => (detail.value?.actions?.length ?? 0) > 0);

/**
 * 审批意见是否已填写（去空白）——审批动作的前置条件。
 *
 * 动作按钮的 `disabled` 与 `onAction` 的守卫共用这一个口径，避免「按钮可点但提交被拦」
 * 这类前端自相矛盾的状态。纯空白字符不算填写。
 */
const canSubmitAction = computed(() => comment.value.trim().length > 0);
/** 从审批详情直接打开合并申请弹窗（当前任务客户为合并源） */
const onLaunchMerge = () => {
  if (detail.value?.oneId) openDialog('merge', { oneId: detail.value.oneId, name: detail.value.name });
};

/** 场景显示名（IMPORT → 批量导入确认；再退 SCENE_TEXT 场景编码映射；客户类后端已存中文，原样显示） */
const sceneText = computed(() => {
  const s = detail.value?.scene ?? '';
  return BIZ_TYPE_TEXT[s] ?? SCENE_TEXT[s] ?? s;
});

/** 治理证据：后端以 JSON 快照下发，逐条渲染为「标签 / 值」；非 JSON 时原样展示 */
const evidenceRows = computed<Array<{ label: string; value: string }>>(() => {
  const raw: unknown = detail.value?.evidence;
  // 后端可能下发对象（JSON 列）或 JSON 字符串（旧快照），两种形态都兼容
  let obj: Record<string, unknown> | null = null;
  if (raw && typeof raw === 'object') {
    obj = raw as Record<string, unknown>;
  } else {
    const text = String(raw ?? '').trim();
    if (text.startsWith('{')) {
      try { obj = JSON.parse(text) as Record<string, unknown>; } catch { obj = null; }
    }
  }
  if (!obj) return [];
  return Object.entries(obj).map(([label, value]) => ({
    label,
    value: value === null || value === undefined ? '—' : String(value)
  }));
});

/**
 * 候选字段级对比（借鉴 DCR Matching Review：绿=一致 / 红=不一致 / 灰=空缺）。
 * 后端 evidence JSON 在疑似/精准重复时成对下发「申请X / 候选X」键；
 * 旧数据缺申请侧键时按「空缺」降级展示，不报错。
 */
interface CandidateCompareRow {
  label: string;
  incoming: string;
  existing: string;
  status: DuplicateFieldStatus;
}
const CAND_ONE_ID_KEY = '候选One ID';
const CAND_SIDE_KEYS = [
  '信用代码',
  '注册地址',
  '候选名称',
  '候选信用代码',
  '候选经营地址',
  '候选BU',
  '候选来源系统',
  '跨BU'
];
const compareRow = (label: string, incoming: string, existing: string): CandidateCompareRow => {
  const normalize = (value: string) => {
    const text = (value ?? '').trim();
    return !text || text === '未提供' || text === '—' ? '' : text;
  };
  const a = normalize(incoming);
  const b = normalize(existing);
  const status: DuplicateFieldStatus = !a || !b ? 'EMPTY' : a === b ? 'MATCH' : 'DIFF';
  return { label, incoming: a, existing: b, status };
};
const candidateCompare = computed<CandidateCompareRow[]>(() => {
  const map = new Map(evidenceRows.value.map(row => [row.label, row.value]));
  if (!map.has(CAND_ONE_ID_KEY)) return [];
  const get = (key: string) => map.get(key) ?? '';
  return [
    compareRow('客户名称', get('申请名称'), get('候选名称')),
    compareRow('统一社会信用代码', get('信用代码'), get('候选信用代码')),
    compareRow('经营地址', get('注册地址'), get('候选经营地址')),
    compareRow('所属 BU', get('申请BU'), get('候选BU')),
    compareRow('来源系统', get('申请来源系统'), get('候选来源系统'))
  ];
});
/**
 * 对比表是否真有可比数据。
 * <p>
 * 历史任务的 evidence 里没有成对的申请侧 / 候选侧字段，五行全是「（空）」——
 * 摆一张全空的对比表比不摆更糟（看着像「证据齐全但字段缺失」）。
 * 无可比数据时整块隐藏，退回纯文本证据列表。
 */
const hasCompare = computed(() => candidateCompare.value.some(row => row.incoming || row.existing));
/** 已进入候选对比的字段不再重复平铺（无可比数据时不做过滤，避免关键键位被吃掉） */
const evidenceRest = computed(() =>
  hasCompare.value ? evidenceRows.value.filter(row => !CAND_SIDE_KEYS.includes(row.label)) : evidenceRows.value
);
const candOneId = computed(() => {
  const map = new Map(evidenceRows.value.map(row => [row.label, row.value]));
  return map.get(CAND_ONE_ID_KEY) ?? '';
});
/**
 * 命中的是「在途申请」而非已发布主档。
 * <p>
 * 两者处置完全不同：在途申请还不是主档，把它说成「关联后转为对该 One ID 主档的更新」
 * 是错的——库里那条主档还不存在，正确处置是撤回本单 / 确认为不同主体 / 退回修正，
 * 后端 _is_in_flight_duplicate 也是按这套动作下发的，提示文案必须跟上。
 */
const isInFlightCand = computed(() => {
  const map = new Map(evidenceRows.value.map(row => [row.label, row.value]));
  return (map.get('在途申请') ?? '').trim() === '是' || (map.get('命中来源') ?? '').includes('在途');
});
const candCrossBu = computed(() => {
  const map = new Map(evidenceRows.value.map(row => [row.label, row.value]));
  // 兼容两种写法：后端历史上写过「是/否」，判定口径与页面文案保持中文
  const flag = (map.get('跨BU') ?? '').trim().toUpperCase();
  return flag === 'Y' || flag === '是';
});
const CMP_FLAG_TEXT: Record<DuplicateFieldStatus, string> = { MATCH: '一致', DIFF: '不一致', EMPTY: '空缺' };
const CMP_FLAG_TAG: Record<DuplicateFieldStatus, 'success' | 'danger' | 'info'> = {
  MATCH: 'success',
  DIFF: 'danger',
  EMPTY: 'info'
};
const cmpFlagText = (status: DuplicateFieldStatus) => CMP_FLAG_TEXT[status] ?? status;
const cmpFlagTag = (status: DuplicateFieldStatus) => CMP_FLAG_TAG[status] ?? 'info';

/** 当前 Tab 的数据集（由服务端按分类 + 分页返回，与该页签的 total 一致） */
const baseTasks = computed<ApprovalTaskVO[]>(() => allTasks.value);

/** 在基础数据集上叠加统一筛选条件（任务类型 / BU / 风险 / 关键词） */
const visibleTasks = computed<ApprovalTaskVO[]>(() => {
  const kw = filter.keyword.trim().toLowerCase();
  return baseTasks.value.filter(t => {
    const matchType = !filter.taskType || t.taskType === filter.taskType;
    const matchBu = !filter.bu || t.bu === filter.bu;
    const matchRisk = !filter.risk || t.risk === filter.risk;
    const matchKw =
      !kw ||
      t.taskId.toLowerCase().includes(kw) ||
      t.customerName.toLowerCase().includes(kw) ||
      (t.oneId ?? '').toLowerCase().includes(kw);
    return matchType && matchBu && matchRisk && matchKw;
  });
});

const onTabChange = () => {
  pageNum.value = 1;
  selectedId.value = '';
  selectedRow.value = null;
  detail.value = null;
  comment.value = '';
  // 分类在服务端切换，切页签必须重新取数，否则列表仍是上一个分类的结果（测试报告 BUG-6）
  void loadData();
};

const applyFilter = () => {
  /* 筛选已通过 visibleTasks 计算属性实时生效，这里仅用于「查询」按钮的点击反馈 */
};

/**
 * 点行选中：右侧速览加载只读概要；审批意见与动作在「进入审批」弹窗中完成。
 *
 * 这里必须 try/catch：取详情是异步请求，一旦后端报错，未捕获的 Promise 异常会让
 * `detail` 一直停在 null，右侧面板保持「选择左侧任务查看概要」的空态，
 * 表现为「点了行没反应」（测试报告 P1-7）。
 */
const onRowSelect = async (row: ApprovalTaskVO | null) => {
  if (!row) return;
  // 同时挂了 current-change 与 row-click（点击任务行必须能展开右侧详情，测试报告 BUG-PY-02）。
  // 两个事件在同一次点击里会先后触发，用「正在取详情的任务号」防重入，避免重复请求与闪烁。
  if (loadingDetailId.value === row.taskId) return;
  selectedId.value = row.taskId;
  selectedRow.value = row;
  detail.value = null;
  loadingDetailId.value = row.taskId;
  try {
    detail.value = await getApprovalTaskDetail(row.taskId);
  } catch (error) {
    ElMessage.error(`加载任务 ${row.taskId} 详情失败：${(error as Error)?.message ?? '未知错误'}`);
  } finally {
    loadingDetailId.value = '';
  }
};

/** 进入审批：打开宽弹窗（完整治理证据 + 审批意见 + 动作按钮） */
const openApproval = () => {
  if (detail.value) detailOpen.value = true;
};

/** 弹窗标题：任务编号 + 客户/主题 */
const detailTitle = computed(() => (detail.value ? `${detail.value.id} · ${detail.value.name}` : '审批详情'));

/** 打开流程跟踪弹窗（泳道图步骤条 + SpiffWorkflow 实例进度） */
const onOpenFlowTrace = () => {
  const row = selectedRow.value;
  if (!row) return;
  openDialog('flowTrace', { taskNo: row.taskId, detailType: row.detailType });
};

/** HTML 转义：确认框允许富文本，客户名等来自业务数据，需防止标签注入 */
const ESC_MAP: Record<string, string> = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
const esc = (value: unknown) => String(value ?? '').replace(/[&<>"']/g, ch => ESC_MAP[ch]);

/**
 * 动作二次确认文案。
 *
 * 这些按钮点下去会真实改动主档并推进流程（合并会并入主档、排除重复会新建独立 One ID、
 * 退回会挂起流程），误点不可撤销，因此提交前统一下发确认。
 * 文案按动作语义差异化，明确「确认后会发生什么」，而不是笼统的「确定执行吗？」。
 */
const buildConfirm = (act: { key: string; label: string }) => {
  const d = detail.value;
  const target = d ? `<b>${esc(d.name)}</b>（任务 ${esc(d.id)}）` : '当前任务';
  const cand = candOneId.value ? `<b>${esc(candOneId.value)}</b>` : '命中主档';

  switch ((act.key || '').toUpperCase()) {
    // 命中存量时后端把 APPROVE 的动作名下发为「确认合并」，确认文案需跟随（BUG-12 口径）
    case 'MERGE':
    case 'APPROVE':
      // 未命中重复（NEW 场景）时才是纯批准新建
      if (candOneId.value) {
        return {
          title: '确认执行合并？',
          html: `将对 ${target} 执行<b>合并</b>：申请数据并入命中主档 ${cand}，不再新建客户。<br/>合并会补全主档空字段、把源记录标记为「已并入」，操作<b>不可撤销</b>。`,
          type: 'warning' as const
        };
      }
      return {
        title: '确认批准？',
        html: `将批准 ${target}：流程流转至结束节点，按申请内容生成客户 One ID，申请资料写入主档。`,
        type: 'warning' as const
      };
    case 'EXCLUDE':
      return {
        title: '确认排除重复？',
        html: `将忽略对 ${cand} 的重复命中，为 ${target} <b>新建独立的 One ID</b>，不与命中主档建立关联。<br/>请确认二者确实不是同一家客户。`,
        type: 'warning' as const
      };
    case 'RETURN':
      // 两级人工审批各退一级（总设计故事一：创建 → BU Scope 初审 → GC Scope 决策）：
      // GC 决策退回 → 只退到 BU Scope 初审补证据；BU 初审退回 → 回申请人改稿重报。
      // 文案必须与后端退回目标节点一致，否则页面说「退回申请人」而流程停在
      // BU Scope 初审（或反之），是最难排查的一类口径漂移。
      if (scope.value === 'gc') {
        return {
          title: '确认退回？',
          html: `将把 ${target} 退回 <b>BU Scope 初审</b>补充证据：本单<b>不会</b>直接打回申请人，`
            + `由 BU Steward 补齐材料后重新提交或再升级，届时再回到 GC 决策。`,
          type: 'warning' as const
        };
      }
      return {
        title: '确认退回？',
        html: `将把 ${target} 退回<b>申请人（创建客户申请）</b>修改重报：流程挂起在「创建客户申请」，`
          + `申请人改稿重新提交后再次进入 BU Scope 初审。`,
        type: 'warning' as const
      };
    case 'ESCALATE':
      return {
        title: '确认升级？',
        html: `将把 ${target} 升级至 <b>GC 治理决策</b>节点，由 GC Steward 复核后给出结论。`,
        type: 'warning' as const
      };
    case 'REJECT':
      return {
        title: '确认拒绝？',
        html: `将拒绝 ${target}：流程终止，申请数据<b>不会写入</b>客户主档。`,
        type: 'error' as const
      };
    case 'LINK':
      return {
        title: '确认关联？',
        html: `将把 ${target} 关联到已有 One ID ${cand}：本申请转为对该 One ID 主档的更新，不再新建客户。`,
        type: 'warning' as const
      };
    case 'CREATE_NEW':
      return {
        title: '确认新建？',
        html: `确认 ${target} 为<b>全新客户</b>：生成新的 One ID，不与任何存量主档关联。`,
        type: 'warning' as const
      };
    case 'WITHDRAW':
      return {
        title: '确认撤回？',
        html: `将撤回 ${target}，关联审批待办同步取消。`,
        type: 'warning' as const
      };
    default:
      return {
        title: `确认执行「${act.label}」？`,
        html: `将对 ${target} 执行「${esc(act.label)}」，该操作会写入审批轨迹并推进流程。`,
        type: 'info' as const
      };
  }
};

/** 确认按钮文案跟随后端下发的动作名（动作名本身已含「确认」时不再重复叠加） */
const confirmTextOf = (label: string) => (label.startsWith('确认') ? label : `确认${label.replace(/·/g, ' ')}`);

/**
 * 提交动作：先弹确认，用户确认后才真正调用后端。
 * 取消 / 关闭确认框一律视为放弃，不提交、不报错。
 *
 * 前置条件：审批意见必填。按钮已按 `canSubmitAction` 置灰，这里再做一道守卫，
 * 防止键盘回车 / 程序化触发绕过禁用态，并顺带把焦点拉回输入框引导补填。
 */
const onAction = async (act: { key: string; label: string; type?: string }) => {
  if (!detail.value) return;
  const opinion = comment.value.trim();
  if (!opinion) {
    ElMessage.warning('请先填写审批意见，再执行审批动作');
    commentRef.value?.focus?.();
    return;
  }
  const ask = buildConfirm(act);
  try {
    await ElMessageBox.confirm(ask.html, ask.title, {
      type: ask.type,
      confirmButtonText: confirmTextOf(act.label),
      cancelButtonText: '取消',
      dangerouslyUseHTMLString: true,
      customClass: 'ap-action-confirm'
    });
  } catch {
    return;
  }
  submitting.value = true;
  try {
    await submitApprovalAction({
      taskId: detail.value.id,
      actionType: act.key,
      opinion
    });
    ElMessage.success(`已执行「${act.label}」，意见：${opinion}`);
    comment.value = '';
    detail.value = null;
    detailOpen.value = false;
    selectedId.value = '';
    selectedRow.value = null;
    await loadData();
    refreshBadge();
  } finally {
    submitting.value = false;
  }
};

/**
 * 按当前页签分类从服务端取数（分页在服务端完成，避免前端合并三类导致的翻页丢数据）。
 * KPI 仍按 Scope 全量统计，与页签列表口径独立。
 */
const loadData = async () => {
  loading.value = true;
  try {
    const [k, t] = await Promise.all([
      getApprovalKpis(scope.value),
      listApprovalTasksByCategory(scope.value, activeCategory.value, pageNum.value, pageSize.value)
    ]);
    kpis.value = k;
    allTasks.value = t.rows;
    total.value = t.total;
    loadError.value = '';
  } catch (error) {
    loadError.value = describeError(error, '待办队列');
    allTasks.value = [];
    total.value = 0;
  } finally {
    loading.value = false;
    // KPI 行 / Tab 高度稳定后表格顶部才准；数据到位后重算一次固定分页位置
    requestAnimationFrame(recalc);
  }
};

/** 切换角色时重新拉取对应 Scope 数据（页签不变，直接按当前分类重查） */
watch(scope, () => {
  pageNum.value = 1;
  selectedId.value = '';
  selectedRow.value = null;
  detail.value = null;
  comment.value = '';
  void loadData();
});

onMounted(loadData);
</script>
