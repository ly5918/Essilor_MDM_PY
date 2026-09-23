<template>
  <section class="page list-page">
    <!-- 筛选条件 / 操作区（降噪：去掉独立卡头与整条彩色提示，提示压成一行小字） -->
    <el-card class="page-card" shadow="never" :body-style="{ padding: '14px 20px 12px' }">
      <div class="card-toolbar">
        <el-input
          v-model="query.keyword"
          :placeholder="view === 'master' ? '名称、One ID、信用代码' : '名称、One ID、信用代码、申请编号'"
          clearable
          style="width: 260px"
          @keyup.enter="onSearch"
        />
        <el-select v-model="query.bu" placeholder="全部BU" clearable style="width: 150px">
          <el-option v-for="bu in BU_OPTIONS" :key="bu" :label="bu" :value="bu" />
        </el-select>
        <el-select v-model="query.customerType" placeholder="全部客户类型" clearable style="width: 150px">
          <el-option v-for="type in CUSTOMER_TYPE_OPTIONS" :key="type" :label="type" :value="type" />
        </el-select>
        <!--
          状态下拉随视图切换：主档视图只可能查到 active / inactive / merged / archived（Golden Record），
          申请态（pending / returned / rejected）在「处理中申请」视图里查——两套字典分开，避免误导。
        -->
        <el-select v-model="query.status" placeholder="全部状态" clearable style="width: 140px">
          <el-option v-for="item in statusOptions" :key="item.value" :label="item.label" :value="item.value" />
        </el-select>
        <el-button type="primary" plain icon="Search" @click="onSearch">查询</el-button>
        <el-button icon="Refresh" @click="onReset">重置</el-button>
      </div>

      <div class="filter-meta">
        <i class="filter-led" :class="readOnly ? 'is-readonly' : 'is-editable'"></i>
        <b>数据权限：{{ role.scope }}</b>
        <span class="filter-sep">·</span>
        <span>{{ readOnly ? '只读查询，不显示创建、编辑、停用按钮' : '记录、字段和操作按钮按角色与 Scope 动态控制' }}</span>
        <span class="filter-sep">·</span>
        <span>条件变化后自动查询</span>
      </div>
    </el-card>

    <!--
      重复核验汇总条（仅主档视图）：本视图唯一的「跨行聚合」提示。
      为什么必须有：同一家客户被重复提交后，两条主档记录的 One ID 不同，
      在列表里各自成行、看不出关联。这里按统一社会信用代码把整组聚合出来并显性提示；
      服务端口径把在途申请单也计入同主体组，所以「在途」提示依然准确。
    -->
    <el-card
      v-if="view === 'master' && dupSummary && dupSummary.groups > 0"
      class="page-card dup-banner"
      shadow="never"
      :body-style="{ padding: '10px 20px' }"
    >
      <span class="dup-banner-icon">⚠</span>
      <div class="dup-banner-text">
        <b>检测到 {{ dupSummary.groups }} 组重复客户</b>
        <span>
          共 {{ dupSummary.rows }} 条记录使用了相同的统一社会信用代码，其中
          <em v-if="dupSummary.inFlightGroups > 0">{{ dupSummary.inFlightGroups }} 组包含「在途申请」（尚未审批完成的申请）</em>
          <em v-else>暂无未完成的在途申请</em>。
        </span>
      </div>
      <!-- 点客户名 → 直接把列表筛到该客户，两条记录并排出现，不用去猜哪条是重复的 -->
      <div class="dup-banner-chips">
        <button v-for="g in dupSummary.samples" :key="g.key" class="dup-chip" @click="focusGroup(g)">
          {{ g.name }}
          <em class="dup-chip-n">×{{ g.size }}</em>
          <em v-if="g.inFlight" class="dup-chip-flight">在途</em>
        </button>
      </div>
    </el-card>

    <!-- 客户列表：主档视图 / 处理中申请视图（申请态与主档分离） -->
    <el-card class="page-card" shadow="never" :body-style="{ padding: '0' }">
      <template #header>
        <div class="cust-head">
          <span class="card-title">{{ view === 'master' ? '客户主档列表' : '处理中申请' }}</span>
          <!--
            视图由**菜单页**决定（客户管理 › 已生效主档 / 处理中申请），不再在卡头放分段按钮：
            分段按钮把其中一个入口藏在列表里，提交完申请的用户停在主档页看不到自己那条，会以为没提交成功。
            这里只留一句口径说明，告诉用户「另一种记录在哪看」。
          -->
          <span class="cust-head-hint">{{ viewHint }}</span>
        </div>
      </template>

      <!-- 请求失败必须可见：网关 502 / 后端重启时不能把「拿不到数据」呈现成「没有客户」 -->
      <LoadErrorBar :message="loadError" @retry="doQuery" />

      <!-- ============ 主档视图（Golden Record） ============ -->
      <!-- 列宽合计≈960px，可在 1280 宽窗口下完整放下（1280 视口内容区约 975px），因此不出现横向滚动条 -->
      <el-table
        v-if="view === 'master'"
        ref="tableRef"
        v-loading="loading && rows.length > 0"
        element-loading-text="正在加载客户主档…"
        border
        :data="rows"
        :height="tableHeight"
        class="data-table cust-table"
        :row-class-name="rowClass"
      >
        <el-table-column label="One ID" prop="oneId" width="108" fixed="left">
          <template #default="{ row }">
            <!-- 等宽中性色 + 悬浮才变蓝：每行少一个高饱和蓝字，扫描更安静 -->
            <el-tooltip content="查看客户主档详情" placement="top">
              <span class="cust-oneid" @click="onViewDetail(row)">{{ row.oneId }}</span>
            </el-tooltip>
          </template>
        </el-table-column>

        <el-table-column label="客户名称" min-width="142" show-overflow-tooltip>
          <template #default="{ row }">
            <div class="cust-name-cell">
              <span class="cust-name-cn"><DetailValue :value="row.legalName" tip="" /></span>
              <span v-if="row.legalNameEn || row.shortName" class="cust-name-sub">
                {{ row.legalNameEn || row.shortName }}
              </span>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="层级归属" width="78" align="center">
          <template #default="{ row }">
            <el-tag
              v-if="hierarchyOf(row).mounted"
              size="small"
              :type="levelTagType(hierarchyOf(row).level)"
              effect="plain"
            >
              {{ hierarchyOf(row).level }}
            </el-tag>
            <el-tooltip
              v-else-if="hierarchyOf(row).isMaster"
              content="已批准成为主数据，但尚未归位到 A3-A2-A1 层级树；请到「客户层级 → 待归位主数据」归位"
              placement="top"
            >
              <el-tag size="small" type="warning" effect="plain">待归位</el-tag>
            </el-tooltip>
            <DetailValue v-else value="" tip="" />
          </template>
        </el-table-column>

        <el-table-column label="所属 BU" min-width="88">
          <template #default="{ row }">
            <DetailValue :value="row.bu" tip="" />
            <el-tooltip v-if="row.gcScopeFlag === 'Y'" content="跨 BU，全局可见" placement="top">
              <el-tag size="small" type="danger" effect="plain" class="m-l-8">跨BU</el-tag>
            </el-tooltip>
          </template>
        </el-table-column>

        <el-table-column label="统一社会信用代码" min-width="138" show-overflow-tooltip>
          <template #default="{ row }">
            <DetailValue :value="row.creditCode" mono tip="" />
          </template>
        </el-table-column>

        <el-table-column label="来源" min-width="74">
          <template #default="{ row }">
            <DetailValue :value="row.sourceSystem" tip="" />
          </template>
        </el-table-column>

        <el-table-column label="状态" width="96" align="center">
          <template #default="{ row }">
            <div class="cust-status-cell">
              <el-tag :type="customerStatusMeta(row.status).type" size="small">{{ customerStatusMeta(row.status).label }}</el-tag>
              <!--
                重复核验行内标识：与上方汇总条同一口径（按统一社会信用代码分组，服务端整组计算，跨页一致）。
                这里不再依赖 duplicate_flag —— 那是「提交当时是否命中候选」的历史事实，
                先提交的恒 N，会造成「先来的不提示、后来的才提示」这种和直觉相反的提示。
              -->
              <el-tooltip v-if="dupOf(row)" :content="row.dupPeerSummary || '同主体存在多条记录'" placement="top">
                <el-tag class="cust-dup-tag" size="small" :type="dupOf(row)!.inFlight ? 'danger' : 'warning'" effect="plain">
                  {{ dupOf(row)!.label }}
                </el-tag>
              </el-tooltip>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="最近更新" min-width="150" align="center">
          <template #default="{ row }">
            <!-- 完整时间戳：日期 + 时分秒 -->
            <span class="cust-mono">{{ fmtDateTime(row.updatedAt) || '—' }}</span>
          </template>
        </el-table-column>

        <!-- 操作列只留「查看客户」：One ID 生命周期历史已并入详情弹窗的页签，不再单开按钮 -->
        <el-table-column label="操作" width="88" fixed="right" align="center">
          <template #default="{ row }">
            <el-button link type="primary" @click="onViewDetail(row)">查看客户</el-button>
          </template>
        </el-table-column>

        <!--
          首屏加载用骨架屏占位，而不是先渲染「暂无数据 共 0 条」再跳出数据：
          列表进页面要先查库（服务端分页 + 层级索引），此前这段空窗会被误读为「没有客户」（测试报告 BUG-7）。
        -->
        <template #empty>
          <div v-if="loading" class="cust-empty-loading">
            <el-skeleton animated :rows="4" />
            <span class="cust-empty-tip">正在加载客户主档…</span>
          </div>
          <span v-else-if="loadError">加载失败，请点击上方「重新加载」</span>
          <span v-else>暂无数据</span>
        </template>
      </el-table>

      <!-- ============ 处理中申请视图（申请态与主档分离） ============ -->
      <el-table
        v-else
        ref="tableRef"
        v-loading="loading && appRows.length > 0"
        element-loading-text="正在加载处理中申请…"
        border
        :data="appRows"
        :height="tableHeight"
        class="data-table cust-table"
        :row-class-name="rowClass"
      >
        <el-table-column label="申请编号" prop="appNo" width="150" fixed="left">
          <template #default="{ row }">
            <el-tooltip content="查看流程跟踪" placement="top">
              <span class="cust-oneid" @click="onViewFlow(row)">{{ row.appNo }}</span>
            </el-tooltip>
          </template>
        </el-table-column>

        <el-table-column label="客户名称" min-width="142" show-overflow-tooltip>
          <template #default="{ row }">
            <div class="cust-name-cell">
              <span class="cust-name-cn"><DetailValue :value="row.legalName" tip="" /></span>
              <span v-if="row.legalNameEn || row.shortName" class="cust-name-sub">
                {{ row.legalNameEn || row.shortName }}
              </span>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="One ID" prop="oneId" width="108">
          <template #default="{ row }">
            <el-tooltip
              content="提交时预分配的 One ID；审批通过后正式发布为主档，拒绝 / 关联已有则作废保留"
              placement="top"
            >
              <span class="cust-mono">{{ row.oneId }}</span>
            </el-tooltip>
          </template>
        </el-table-column>

        <el-table-column label="所属 BU" min-width="88">
          <template #default="{ row }">
            <DetailValue :value="row.bu" tip="" />
            <el-tooltip v-if="row.gcScopeFlag === 'Y'" content="跨 BU，全局可见" placement="top">
              <el-tag size="small" type="danger" effect="plain" class="m-l-8">跨BU</el-tag>
            </el-tooltip>
          </template>
        </el-table-column>

        <el-table-column label="统一社会信用代码" min-width="138" show-overflow-tooltip>
          <template #default="{ row }">
            <DetailValue :value="row.creditCode" mono tip="" />
          </template>
        </el-table-column>

        <el-table-column label="状态" width="110" align="center">
          <template #default="{ row }">
            <div class="cust-status-cell">
              <el-tag :type="applicationStatusMeta(row.status).type" size="small">
                {{ applicationStatusMeta(row.status).label }}
              </el-tag>
              <el-tooltip v-if="dupOf(row)" :content="row.dupPeerSummary || '同主体存在多条记录'" placement="top">
                <el-tag class="cust-dup-tag" size="small" :type="dupOf(row)!.inFlight ? 'danger' : 'warning'" effect="plain">
                  {{ dupOf(row)!.label }}
                </el-tag>
              </el-tooltip>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="当前节点" min-width="110" align="center">
          <template #default="{ row }">
            <DetailValue :value="row.currentNodeName" tip="" />
          </template>
        </el-table-column>

        <el-table-column label="提交时间" min-width="150" align="center">
          <template #default="{ row }">
            <span class="cust-mono">{{ fmtDateTime(row.createdAt) || '—' }}</span>
          </template>
        </el-table-column>

        <!-- 申请未发布成主档，没有「客户详情」可看；主操作落到流程跟踪，被退回行加「修改重报」 -->
        <el-table-column label="操作" width="150" fixed="right" align="center">
          <template #default="{ row }">
            <el-button link type="primary" @click="onViewFlow(row)">查看流程</el-button>
            <el-tooltip
              content="本申请已被退回，修改后重新提交，再次进入 BU Scope 初审"
              placement="top"
            >
              <el-button
                v-if="row.status === 'returned'"
                link
                type="warning"
                @click="onOpenResubmit(row)"
              >修改重报</el-button>
            </el-tooltip>
          </template>
        </el-table-column>

        <template #empty>
          <div v-if="loading" class="cust-empty-loading">
            <el-skeleton animated :rows="4" />
            <span class="cust-empty-tip">正在加载处理中申请…</span>
          </div>
          <span v-else-if="loadError">加载失败，请点击上方「重新加载」</span>
          <span v-else>暂无在途申请</span>
        </template>
      </el-table>

      <div v-if="(view === 'master' ? total : appTotal) > 0" class="cust-pager">
        <el-pagination
          v-model:current-page="page.current"
          v-model:page-size="page.size"
          :total="view === 'master' ? total : appTotal"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          background
        />
      </div>
    </el-card>

    <!-- ============ 修改重报弹窗（两级审批闭环：BU 初审退回 → 申请人修改 → 重进 BU 初审） ============ -->
    <el-dialog
      v-model="resubmitVisible"
      title="修改重报"
      width="560px"
      append-to-body
      destroy-on-close
      class="resubmit-dialog"
    >
      <el-alert
        type="warning"
        :closable="false"
        class="rs-tip"
        title="本申请已被 BU Scope 退回。修改后重新提交：重新执行查重与 DQ 评分，并再次进入 BU Scope 初审。"
        show-icon
      />
      <el-form :model="resubmitForm" label-width="118px">
        <el-form-item label="申请编号">
          <span class="cust-mono">{{ resubmitForm.appNo }}</span>
        </el-form-item>
        <el-form-item label="客户法定名称" required>
          <el-input v-model="resubmitForm.legalName" maxlength="200" placeholder="客户法定名称（必填）" />
        </el-form-item>
        <el-form-item label="统一社会信用代码">
          <el-input v-model="resubmitForm.creditCode" maxlength="32" placeholder="18 位统一社会信用代码" />
        </el-form-item>
        <el-form-item label="注册地址">
          <el-input v-model="resubmitForm.address" maxlength="200" placeholder="注册 / 经营地址（查重主依据之一）" />
        </el-form-item>
        <el-form-item label="联系人">
          <el-input v-model="resubmitForm.contactName" maxlength="50" />
        </el-form-item>
        <el-form-item label="联系电话">
          <el-input v-model="resubmitForm.contactPhone" maxlength="30" />
        </el-form-item>
        <el-form-item label="修改说明">
          <el-input
            v-model="resubmitForm.remark"
            type="textarea"
            :rows="2"
            maxlength="200"
            show-word-limit
            placeholder="填写本次修改要点，将记入流程轨迹"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="resubmitVisible = false">取消</el-button>
        <el-button type="primary" :loading="resubmitting" @click="onResubmit">确认重报</el-button>
      </template>
    </el-dialog>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue';
import { ElMessage } from 'element-plus';
import {
  listCustomerApplications,
  listCustomers,
  resubmitCustomerApplication
} from '@/api/demo/cmdPoc';
import type {
  CustomerApplicationQuery,
  CustomerApplicationVO,
  CustomerQuery,
  CustomerVO
} from '@/api/demo/cmdPoc/types';
import DetailValue from '../DetailValue.vue';
import LoadErrorBar from '../LoadErrorBar.vue';
import { describeError } from '../../composables/loadError';
import { useCmdPoc } from '../../composables/useCmdPoc';
import { useListTableHeight } from '../../composables/useListTableHeight';
import {
  APPLICATION_STATUS_OPTIONS,
  BU_OPTIONS,
  CUSTOMER_STATUS_OPTIONS,
  CUSTOMER_TYPE_OPTIONS,
  applicationStatusMeta,
  customerStatusMeta
} from '../../constants/options';

defineOptions({ name: 'CmdPocCustomersPanel' });

/**
 * 初始视图由所在菜单页决定（外壳 index.vue 传）：'master' 已生效主档 / 'inFlight' 处理中申请。
 * 组件用 `currentPage` 作为 key，切换菜单即重建，因此这里只读一次初值。
 */
const props = defineProps<{ defaultView?: 'master' | 'inFlight' }>();

const { readOnly, role, openDialog, hierarchyIndex, loadHierarchyIndex, badgeVersion } = useCmdPoc();

/** 表格高度自适应：分页条固定在内容区底部，不随数据条数浮动 */
const { tableRef, tableHeight, recalc } = useListTableHeight(70);

/**
 * 视图：master = 已生效主档（Golden Record）；inFlight = 处理中申请。
 * <p>
 * 申请态与主档分离后，两者是不同的表、不同的详情：主档视图做「统一查询」，
 * 处理中视图做「跟进 + 跳流程」，不再混在一张列表里，也不再由页内分段按钮切换。
 */
const view = ref<'master' | 'inFlight'>(props.defaultView ?? 'master');

/** 卡头右侧口径说明：明确「当前看的是哪一类记录」「另一种去哪看」 */
const viewHint = computed(() =>
  view.value === 'master'
    ? '仅含已发布为 Golden Record 的客户；尚未审批完成的申请见「处理中申请」'
    : '尚未审批完成的申请（待审批 / 已退回）；审批通过后发布为「已生效主档」'
);

const loading = ref(true);
/** 请求失败原因：非空时页面顶部展示错误条 + 「重新加载」，避免把「取不到」呈现成「没有」 */
const loadError = ref('');
const query = ref<{ keyword: string; bu: string; customerType: string; status?: string }>({
  keyword: '',
  bu: '',
  customerType: '',
  status: undefined
});
const page = ref({ current: 1, size: 10 });

/** 当前页列表（服务端分页，每次查询都实时读库） */
const rows = ref<CustomerVO[]>([]);
/** 当前筛选条件命中的总条数（用于分页器） */
const total = ref(0);

/** 处理中申请视图数据 */
const appRows = ref<CustomerApplicationVO[]>([]);
const appTotal = ref(0);
/** 申请单在途条数角标已上移到左侧菜单（「客户管理 › 处理中申请」），面板内不再重复展示 */

/** 状态下拉随视图切换：主档字典 / 申请单字典 */
const statusOptions = computed(() => (view.value === 'master' ? CUSTOMER_STATUS_OPTIONS : APPLICATION_STATUS_OPTIONS));

/**
 * 客户 → 层级归属（客户列表「层级归属」列）
 * - 已在 A3-A2-A1 树上：显示 A3 / A2 / A1
 * - 已批准成为主数据但尚未归位：显示「待归位」，并引导到「客户层级 → 待归位主数据」
 * - 其余（待审批 / 驳回 / 停用）：不参与层级，显示 —
 */
const hierarchyOf = (row: unknown) => {
  const customer = row as CustomerVO;
  const hit = hierarchyIndex.value.get(customer.oneId);
  if (hit) return { ...hit, isMaster: true };
  return { level: '—', path: '', mounted: false, isMaster: customer.status === 'active' };
};

const levelTagType = (level: string) => (level === 'A3' ? 'primary' : level === 'A2' ? 'warning' : 'success');

/** 最近更新列展示完整时间戳：日期 + 时分秒 */
const fmtDateTime = (value?: string) => (value ? value.replace('T', ' ').slice(0, 19) : '');

/**
 * 疑似重复行整行淡红，扫列表时最先看到风险数据。
 * <p>
 * 判定用「同主体组内条数」（dupGroupSize）而不是单看 duplicate_flag：
 * duplicate_flag 只在「提交当时命中了候选」时为 Y，于是同一组里先提交的那条是 N、不会变色，
 * 用户会看到两条待审批记录只有一条被标红，反而更迷惑。
 */
const rowClass = ({ row }: { row: Record<string, unknown> }) =>
  (row.duplicateFlag === 'Y' || ((row.dupGroupSize as number | undefined) ?? 1) > 1 ? 'cust-row-warn' : '');

/**
 * 行内「重复核验」标签：null 表示该行无同主体重复。
 * <p>
 * 入参放宽为 Record&lt;string, any&gt;：模板里 el-table 提供的 row 静态类型是 DefaultRow，
 * 直接标 CustomerVO 会让 vue-tsc 报「缺少 oneId/legalName…」（运行时数据源本就是 CustomerVO）。
 * 两个视图共用：主档行与申请单行都由服务端下发同名的 dupGroupSize / dupInFlightCount。
 */
const dupOf = (row: Record<string, any>) => {
  const size = (row.dupGroupSize as number | undefined) ?? 1;
  if (size < 2) return null;
  const inFlight = (row.dupInFlightCount as number | undefined) ?? 0;
  return {
    inFlight: inFlight > 0,
    label: inFlight > 0 ? `重复·在途${inFlight}` : `重复 ${size}`
  };
};

/**
 * 重复核验汇总（整组口径，不受分页影响；仅主档视图展示）。
 * <p>
 * 列表是服务端分页（每页 10 条），同一组的两条记录很可能落在不同页上
 * （南京视界案例：一条在第 1 页、一条在第 5 页），只看当前页会漏判。
 * 因此这里按当前筛选条件再取一次「权限内全量」（不传 pageNum / pageSize），
 * 以统一社会信用代码分组统计——数据量在 POC 规模（数十条）下开销可忽略。
 */
const dupSummary = ref<{
  groups: number;
  rows: number;
  inFlightGroups: number;
  samples: Array<{ key: string; name: string; size: number; inFlight: boolean }>;
} | null>(null);

const loadDuplicateSummary = async () => {
  try {
    const all = await listCustomers({ ...currentFilters() } as CustomerQuery);
    // 只收「服务端判定为同主体多条」的行（dupGroupSize > 1）：
    // 服务端口径已排除 merged / rejected / draft，这里不再自行按状态过滤，
    // 否则会出现「汇总条把已合并的记录算成重复、行内标签却不显示」的自相矛盾。
    const groups = new Map<string, CustomerVO[]>();
    all.rows.forEach(row => {
      if ((row.dupGroupSize ?? 1) < 2) return;
      const key = (row.creditCode || '').trim().toUpperCase();
      if (!key) return;
      const list = groups.get(key) ?? [];
      list.push(row);
      groups.set(key, list);
    });
    let g = 0;
    let r = 0;
    let flight = 0;
    const samples: Array<{ key: string; name: string; size: number; inFlight: boolean }> = [];
    groups.forEach((list, key) => {
      g += 1;
      // 组内条数取服务端值（同组每行相同），不用本地 list.length —— 本地会被分页/筛选截断
      const size = list.reduce((max, item) => Math.max(max, item.dupGroupSize ?? 1), list.length);
      r += size;
      const hasFlight = list.some(item => (item.dupInFlightCount ?? 0) > 0);
      if (hasFlight) flight += 1;
      samples.push({ key, name: list[0].legalName || key, size, inFlight: hasFlight });
    });
    // 样本按「含在途优先 + 条数多优先」，只留前 3 个，避免汇总条把列表挤下去
    samples.sort((a, b) => Number(b.inFlight) - Number(a.inFlight) || b.size - a.size);
    dupSummary.value = { groups: g, rows: r, inFlightGroups: flight, samples: samples.slice(0, 3) };
  } catch {
    // 汇总只是辅助提示，取不到就不展示，不能影响主列表（主列表有自己的错误条）
    dupSummary.value = null;
  }
};

/** 点汇总条里的客户名：把列表筛到该客户，两条重复记录并排出现 */
const focusGroup = (group: { name: string }) => {
  query.value.keyword = group.name;
  page.value.current = 1;
  scheduleQuery(0, true);
};

/** 当前筛选条件（列表与指标带共用，保证口径一致） */
const currentFilters = () => ({
  keyword: query.value.keyword,
  bu: query.value.bu,
  customerType: query.value.customerType,
  status: query.value.status || undefined
});

/**
 * 查询：条件 + 分页一起提交后端，每次都实时查库。
 * 不再做前端本地过滤，数据以数据库当前值为准（他人在别处改动后刷新即可看到）。
 */
const doQuery = async () => {
  loading.value = true;
  try {
    if (view.value === 'master') {
      const pageResult = await listCustomers({
        ...(currentFilters() as CustomerQuery),
        pageNum: page.value.current,
        pageSize: page.value.size
      });
      rows.value = pageResult.rows;
      total.value = pageResult.total;
      loadError.value = '';
      // 重复核验汇总与主列表并行刷新（整组口径，需要不带分页的权限内全量）
      void loadDuplicateSummary();
    } else {
      const pageResult = await listCustomerApplications({
        ...(currentFilters() as CustomerApplicationQuery),
        pageNum: page.value.current,
        pageSize: page.value.size
      });
      appRows.value = pageResult.rows;
      appTotal.value = pageResult.total;
      loadError.value = '';
    }
    // 条件收紧把当前页挤出范围时（例如第 3 页筛完只剩 1 页），自动落到最后一个可用页
    const currentTotal = view.value === 'master' ? total.value : appTotal.value;
    const maxPage = Math.max(1, Math.ceil(currentTotal / page.value.size));
    if (page.value.current > maxPage) {
      page.value.current = maxPage;
      await doQuery();
    }
  } catch (error) {
    // 查询失败时清空列表，避免残留上一次的结果造成误读；
    // 同时把失败原因显性化——502 / 断连时页面必须说「加载失败」，不能只显示「暂无数据」。
    rows.value = [];
    total.value = 0;
    appRows.value = [];
    appTotal.value = 0;
    // 主列表都取不到时，汇总条不能残留上一次的旧数字
    dupSummary.value = null;
    loadError.value = describeError(error, view.value === 'master' ? '客户主档' : '处理中申请');
  } finally {
    loading.value = false;
    recalc();
  }
};

let queryTimer: ReturnType<typeof setTimeout> | undefined;

/**
 * 合并短时间内的多次条件变化，避免一次交互打出多个请求。
 *
 * @param delayMs   延迟（关键字输入用防抖，下拉/分页立即执行）
 * @param resetPage 是否回到第一页（条件变化必须回第一页，否则可能落在越界页）
 */
const scheduleQuery = (delayMs = 0, resetPage = false) => {
  if (resetPage) page.value.current = 1;
  if (queryTimer) clearTimeout(queryTimer);
  queryTimer = setTimeout(() => void doQuery(), delayMs);
};

/** 关键字输入：防抖 400ms 自动查库（输入即查，无需点按钮） */
watch(
  () => query.value.keyword,
  () => scheduleQuery(400, true)
);
/** 下拉条件：变更即查库 */
watch(() => [query.value.bu, query.value.customerType, query.value.status], () => scheduleQuery(0, true));
/** 分页：翻页 / 改每页条数即查库（不回第一页） */
watch(() => [page.value.current, page.value.size], () => scheduleQuery(0));
/** 新建 / 审批等操作后（badgeVersion 自增）自动刷新（菜单角标由侧栏自行刷新） */
watch(badgeVersion, () => scheduleQuery(0));

/** 查询按钮：按当前条件立即查库，列表直接刷新（不再弹出结果弹窗） */
const onSearch = () => scheduleQuery(0, true);

const onReset = () => {
  query.value = { keyword: '', bu: '', customerType: '', status: undefined };
  page.value.current = 1;
  scheduleQuery(0, true);
};

/** 行数据类型由 el-table 统一为 DefaultRow，此处收敛断言，保证模板调用无需类型体操 */
const onViewDetail = (row: unknown) => {
  const customer = row as CustomerVO;
  openDialog('customerDetail', { oneId: customer.oneId, row: { ...customer } });
};

/** 处理中申请的主操作：跳流程跟踪弹窗（申请编号与审批任务编号同值同源） */
const onViewFlow = (row: unknown) => {
  const app = row as CustomerApplicationVO;
  openDialog('flowTrace', {
    taskNo: app.taskNo || app.appNo,
    // 已拒绝的申请流程已走完 → done 视图；其余（待审批 / 退回）→ active 视图
    detailType: app.status === 'rejected' ? 'done' : 'active'
  });
};

/* ---------- 修改重报（两级审批闭环：BU 初审退回 → 申请人修改 → 重进 BU 初审） ---------- */

const resubmitVisible = ref(false);
const resubmitting = ref(false);
const resubmitForm = ref({
  appNo: '',
  legalName: '',
  creditCode: '',
  address: '',
  contactName: '',
  contactPhone: '',
  remark: ''
});

/** 打开重报弹窗：用申请单当前值预填（只有被退回的行才显示入口） */
const onOpenResubmit = (row: unknown) => {
  const app = row as CustomerApplicationVO;
  resubmitForm.value = {
    appNo: app.appNo,
    legalName: app.legalName || '',
    creditCode: app.creditCode || '',
    address: app.address || '',
    contactName: app.contactName || '',
    contactPhone: app.contactPhone || '',
    remark: ''
  };
  resubmitVisible.value = true;
};

/** 确认重报：后端重跑查重 / DQ，并把任务与流程实例拉回 BU Scope 初审 */
const onResubmit = async () => {
  if (!resubmitForm.value.legalName.trim()) {
    ElMessage.warning('客户法定名称不能为空');
    return;
  }
  resubmitting.value = true;
  try {
    const msg = await resubmitCustomerApplication(resubmitForm.value.appNo, {
      legalName: resubmitForm.value.legalName.trim(),
      creditCode: resubmitForm.value.creditCode.trim(),
      address: resubmitForm.value.address.trim(),
      contactName: resubmitForm.value.contactName.trim(),
      contactPhone: resubmitForm.value.contactPhone.trim(),
      remark: resubmitForm.value.remark.trim()
    });
    ElMessage.success(msg);
    resubmitVisible.value = false;
    await doQuery();
  } catch (error) {
    ElMessage.error(describeError(error, '修改重报'));
  } finally {
    resubmitting.value = false;
  }
};

onMounted(async () => {
  await doQuery();
  // 层级归属列的数据来源：层级树（已归位）+ 待归位主数据
  await loadHierarchyIndex();
});

onUnmounted(() => {
  if (queryTimer) clearTimeout(queryTimer);
});
</script>

<style scoped lang="scss">
/* 卡头：标题 + 一行口径说明（说明在窄屏省略号截断，不挤压标题、不换行） */
.cust-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
}

.cust-head-hint {
  flex: 0 1 auto;
  min-width: 0;
  overflow: hidden;
  font-size: 12px;
  color: var(--g-text2);
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 修改重报弹窗：警示条与表单留出间距 */
.rs-tip {
  margin-bottom: 16px;
}

/* 权限与查询说明：压成一行 12px 小字，避免整条彩色 alert 占据一个视觉带 */
.filter-meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0 6px;
  margin-top: 10px;
  font-size: 12px;
  line-height: 1.6;
  color: var(--g-text2);

  b {
    font-weight: 600;
    color: var(--g-text);
  }
}

.filter-led {
  width: 6px;
  height: 6px;
  border-radius: 50%;

  &.is-editable {
    background: #1f9254;
  }

  &.is-readonly {
    background: #909399;
  }
}

.filter-sep {
  opacity: 0.5;
}

.cust-name-cell {
  display: flex;
  flex-direction: column;
  line-height: 1.4;
  min-width: 0;
}

/* 两行都做省略号，避免窄列下文字被硬切（完整值由列级 tooltip 提供） */
.cust-name-cn,
.cust-name-sub {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cust-name-cn {
  color: var(--g-text);
}

.cust-name-sub {
  font-size: 12px;
  color: var(--g-text2);
}

/* One ID / 申请编号：中性色等宽文字，悬浮才变蓝，避免每行两个蓝色链接的视觉噪音 */
.cust-oneid {
  font-family: Consolas, Monaco, monospace;
  font-size: 12px;
  color: var(--g-text);
  white-space: nowrap;
  cursor: pointer;
  transition: color 0.15s;

  &:hover {
    color: var(--el-color-primary);
    text-decoration: underline;
  }
}

/* 等宽 / One ID 链接统一不折行，保证行高一致（列窄时靠省略号而不是换行） */
.cust-mono {
  display: inline-block;
  max-width: 100%;
  overflow: hidden;
  font-family: Consolas, Monaco, monospace;
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
  vertical-align: bottom;
}

.cust-pager {
  display: flex;
  justify-content: flex-end;
  padding: 12px 16px;
}

/* 首屏骨架屏：占满表格空态区域，避免「暂无数据」闪现 */
.cust-empty-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 12px 24px 0;

  :deep(.el-skeleton) {
    width: 100%;
  }
}

.cust-empty-tip {
  font-size: 12px;
  color: var(--g-text2);
}

/**
 * 紧凑表格：列多且要在一屏内放下，通过收紧内边距与字号换取横向空间。
 * 每列横向内边距从框架默认 24px 收到 16px，9 列合计省下约 72px。
 */
.cust-table {
  :deep(.el-table__cell) {
    padding: 7px 0;
  }

  :deep(.cell) {
    padding: 0 8px;
    font-size: 12.5px;
    line-height: 1.45;
  }

  :deep(.el-table__header .cell) {
    font-weight: 600;
  }

  :deep(.el-tag) {
    height: 20px;
    padding: 0 6px;
    font-size: 11.5px;
    line-height: 18px;
  }

  :deep(.el-button.is-link) {
    padding: 2px 0;
    font-size: 12.5px;
  }
}

:deep(.cust-row-warn) {
  --el-table-tr-bg-color: #fdf3f3;
}

/* ===== 重复核验汇总条 =====
   一行放三块：警示图标 / 文案 / 可点的客户名 chip。
   用 warning 色而不是 danger —— 重复不等于错误（同信用代码但确需新建的场景要留通路），
   这里只负责「让业务用户知道」，判定权仍在 Data Steward / GC。 */
.dup-banner {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px 12px;
  margin-top: 10px;
  border-color: var(--el-color-warning-light-5);
  background: var(--el-color-warning-light-9);
}

.dup-banner-icon {
  flex: 0 0 auto;
  font-size: 16px;
  line-height: 1;
  color: var(--el-color-warning);
}

.dup-banner-text {
  flex: 1 1 320px;
  min-width: 0;
  font-size: 12.5px;
  line-height: 1.6;
  color: var(--g-text2);

  b {
    margin-right: 6px;
    font-size: 13px;
    color: var(--g-text);
  }

  em {
    font-style: normal;
    font-weight: 600;
    color: var(--el-color-warning);
  }
}

.dup-banner-chips {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
}

.dup-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  max-width: 240px;
  padding: 2px 8px;
  border: 1px solid var(--el-color-warning-light-5);
  border-radius: 11px;
  background: var(--el-bg-color);
  font-size: 12px;
  color: var(--g-text);
  cursor: pointer;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;

  &:hover {
    border-color: var(--el-color-warning);
    color: var(--el-color-warning);
  }
}

.dup-chip-n {
  flex: 0 0 auto;
  font-style: normal;
  font-weight: 600;
  color: var(--el-color-warning);
}

.dup-chip-flight {
  flex: 0 0 auto;
  padding: 0 4px;
  border-radius: 3px;
  background: var(--el-color-danger);
  font-style: normal;
  font-size: 10.5px;
  color: #fff;
}

/* 状态列两行：状态标签 + 重复核验标签（宽度中性，不新增列，避免 1280 下横向滚动） */
.cust-status-cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
}

:deep(.cust-dup-tag) {
  height: 18px;
  padding: 0 5px;
  font-size: 11px;
  line-height: 16px;
}
</style>
