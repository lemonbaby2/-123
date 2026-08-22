// Copyright (C) CVAT.ai Corporation
//
// SPDX-License-Identifier: MIT

/*
 * CVAT does not currently expose an application-wide localization API. This
 * small overlay translates fixed UI phrases after React/Ant Design render
 * them. Exact matches are intentional: task names, label names, comments and
 * annotation data must never be translated.
 */

const translations: Readonly<Record<string, string>> = Object.freeze({
    'Projects': '项目',
    'Tasks': '任务',
    'Jobs': '作业',
    'Cloud storages': '云存储',
    'Cloud Storages': '云存储',
    'Models': '模型',
    'Analytics': '分析',
    'Organizations': '组织',
    'Requests': '请求',
    'About': '关于',
    'Help': '帮助',
    'Settings': '设置',
    'Menu': '菜单',
    'Fullscreen': '全屏',
    'Exit fullscreen': '退出全屏',
    'Appearance': '外观',
    'Shortcuts': '快捷键',
    'Keyboard shortcuts': '键盘快捷键',
    'Logout': '退出登录',
    'Login': '登录',
    'Register': '注册',
    'Username': '用户名',
    'Password': '密码',
    'Create': '创建',
    'Create new task': '创建新任务',
    'Create new project': '创建新项目',
    'Create task': '创建任务',
    'Create project': '创建项目',
    'Task name': '任务名称',
    'Project name': '项目名称',
    'Name': '名称',
    'Description': '描述',
    'Owner': '所有者',
    'Assignee': '执行人',
    'Subset': '子集',
    'Labels': '标签',
    'Label': '标签',
    'Add label': '添加标签',
    'Add new label': '添加新标签',
    'Select files': '选择文件',
    'My computer': '本机',
    'Remote sources': '远程来源',
    'Connected file share': '已连接文件共享',
    'Advanced configuration': '高级配置',
    'Submit & Open': '提交并打开',
    'Submit & Continue': '提交并继续',
    'Cancel': '取消',
    'Save': '保存',
    'Delete': '删除',
    'Edit': '编辑',
    'Update': '更新',
    'Open': '打开',
    'Close': '关闭',
    'Continue': '继续',
    'Back': '返回',
    'Next': '下一步',
    'Previous': '上一步',
    'Actions': '操作',
    'Status': '状态',
    'Search': '搜索',
    'Filter': '筛选',
    'Sort': '排序',
    'Import': '导入',
    'Export': '导出',
    'Import task': '导入任务',
    'Export task': '导出任务',
    'Import dataset': '导入数据集',
    'Export dataset': '导出数据集',
    'Export annotations': '导出标注',
    'Export task dataset': '导出任务数据集',
    'Download': '下载',
    'Upload': '上传',
    'Format': '格式',
    'Include images': '包含图像',
    'Save images': '保存图像',
    'Quality': '质量',
    'Statistics': '统计',
    'Information': '信息',
    'Workspace': '工作区',
    'Standard': '标准',
    'Review': '复核',
    'Tag annotation': '标签标注',
    'Issues': '问题',
    'Annotations': '标注',
    'Objects': '对象',
    'Details': '详情',
    'Undo': '撤销',
    'Redo': '重做',
    'Finish': '完成',
    'Done': '完成',
    'Apply': '应用',
    'Reset': '重置',
    'Yes': '是',
    'No': '否',
    'Loading...': '加载中...',
    'No data': '暂无数据',
    'No results found': '未找到结果',
    'Draw a rectangle': '绘制矩形框（十字准星）',
    'Draw a polygon': '绘制多边形',
    'Draw a polyline': '绘制折线',
    'Draw points': '绘制点',
    'Draw an ellipse': '绘制椭圆',
    'Draw a cuboid': '绘制长方体',
    'Draw a mask': '绘制遮罩',
    'Draw new rectangle': '绘制新矩形框',
    'Draw new polygon': '绘制新多边形',
    'Draw new polyline': '绘制新折线',
    'Draw new points': '绘制新点',
    'Draw new ellipse': '绘制新椭圆',
    'Draw new cuboid': '绘制新长方体',
    'Draw new mask': '绘制新遮罩',
    'Drawing method': '绘制方式',
    'By 2 Points': '两点对角绘制',
    'By 4 Points': '四个极值点绘制',
    'From rectangle': '从矩形框创建',
    'Number of points:': '点数：',
    'Simplify': '简化',
    'Shape': '形状',
    'Track': '跟踪轨迹',
    'Cursor': '选择工具',
    'Move the image': '移动图像',
    'Fit the image': '适应画布',
    'Rotate clockwise': '顺时针旋转',
    'Rotate anticlockwise': '逆时针旋转',
    'Merge shapes': '合并形状',
    'Group shapes': '组合形状',
    'Split a track': '分割轨迹',
    'Join tracks': '连接轨迹',
    'Slice shape': '切分形状',
    'Propagate': '向后传播',
    'Remove': '移除',
    'Occluded': '遮挡',
    'Outside': '画面外',
    'Keyframe': '关键帧',
    'Frame': '帧',
    'Play': '播放',
    'Pause': '暂停',
    'First frame': '首帧',
    'Last frame': '末帧',
    'Next frame': '下一帧',
    'Previous frame': '上一帧',
    'Save annotations': '保存标注',
    'Automatic annotation': '自动标注',
    'Run automatic annotation': '运行自动标注',
    'Search ...': '搜索...',
    'Search tasks ...': '搜索任务...',
    'Search projects ...': '搜索项目...',
    'Search jobs ...': '搜索作业...',
});

const translatableAttributes = ['title', 'placeholder', 'aria-label'] as const;

function translate(value: string): string | null {
    const leadingWhitespace = value.match(/^\s*/u)?.[0] ?? '';
    const trailingWhitespace = value.match(/\s*$/u)?.[0] ?? '';
    const key = value.trim();
    const translated = translations[key];

    return translated ? `${leadingWhitespace}${translated}${trailingWhitespace}` : null;
}

function localizeElement(element: Element): void {
    if (element.closest('[data-cvat-localization-skip="true"]')) return;

    for (const attribute of translatableAttributes) {
        const value = element.getAttribute(attribute);
        if (value) {
            const translated = translate(value);
            if (translated && translated !== value) element.setAttribute(attribute, translated);
        }
    }

    for (const child of Array.from(element.childNodes)) {
        if (child.nodeType === Node.TEXT_NODE && child.textContent) {
            const translated = translate(child.textContent);
            if (translated && translated !== child.textContent) child.textContent = translated;
        } else if (child.nodeType === Node.ELEMENT_NODE) {
            localizeElement(child as Element);
        }
    }
}

export default function enableChineseLocalization(): void {
    document.documentElement.lang = 'zh-CN';
    localizeElement(document.documentElement);

    const observer = new MutationObserver((mutations) => {
        for (const mutation of mutations) {
            if (mutation.type === 'characterData' && mutation.target.parentElement) {
                localizeElement(mutation.target.parentElement);
            }
            for (const node of Array.from(mutation.addedNodes)) {
                if (node.nodeType === Node.ELEMENT_NODE) localizeElement(node as Element);
                if (node.nodeType === Node.TEXT_NODE && node.parentElement) localizeElement(node.parentElement);
            }
        }
    });

    observer.observe(document.documentElement, {
        childList: true,
        characterData: true,
        subtree: true,
    });
}
