import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import warnings
import os
import re
import matplotlib
from io import BytesIO
import tempfile

# 设置图表字体为英文，避免中文字符问题
matplotlib.use('Agg')
plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans', 'Helvetica', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False
warnings.filterwarnings('ignore')

# 设置图表样式
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (14, 9)  # 增加图表尺寸
plt.rcParams['axes.titlesize'] = 16
plt.rcParams['axes.labelsize'] = 14
plt.rcParams['xtick.labelsize'] = 12
plt.rcParams['ytick.labelsize'] = 12
plt.rcParams['legend.fontsize'] = 12


class ChinaAircraftAnalysisTool:
    def __init__(self):
        # 窄体机型号列表（包括支线机）
        self.narrow_body_models = [
            # Boeing
            '737-600', '737-700', '737-800', '737-900',
            '737 MAX 7', '737 MAX 8', '737 MAX 9', '737 MAX 10',
            # Airbus
            'A318', 'A319', 'A320', 'A321',
            'A319neo', 'A320neo', 'A321neo',
            # COMAC
            'C919', 'C919ER',
            # Regional Jets
            'ARJ21', 'CRJ200', 'CRJ700', 'CRJ900', 'CRJ1000',
            'E170', 'E175', 'E190', 'E195',
            'E190-E2', 'E195-E2',
            'MA60', 'MA600'
        ]

        # 制造商分类
        self.manufacturer_mapping = {
            'AIRBUS': 'Airbus',
            'BOEING': 'Boeing',
            'EMBRAER': 'Embraer',
            'COMAC': 'COMAC',
            'CRAIC': 'COMAC',
            'BOMBARDIER': 'Bombardier',
            'CANADAIR': 'Bombardier',
            'AVIC': 'AVIC',
            'XIAN': 'AVIC',
            'HARBIN': 'AVIC',
            'TEXTRON': 'Textron',
            'CESSNA': 'Textron'
        }

        # 飞机型号座位数映射
        self.seat_capacity_map = {
            # Boeing
            '737-600': 110, '737-700': 126, '737-800': 162,
            '737-900': 180, '737 MAX 7': 138, '737 MAX 8': 178,
            '737 MAX 9': 193, '737 MAX 10': 204,

            # Airbus
            'A318': 107, 'A319': 124, 'A320': 150, 'A321': 185,
            'A319neo': 140, 'A320neo': 165, 'A321neo': 206,

            # COMAC
            'C919': 168, 'C919ER': 192,

            # Regional Jets
            'ARJ21': 78, 'ARJ21-700': 78, 'ARJ21-900': 105,
            'CRJ200': 50, 'CRJ700': 70, 'CRJ900': 90, 'CRJ1000': 104,
            'E170': 72, 'E175': 88, 'E190': 100, 'E195': 124,
            'E190-E2': 106, 'E195-E2': 132,
            'MA60': 60, 'MA600': 60
        }

        # 中国省份列表（用于筛选）
        self.china_states = [
            'Beijing', 'Chongqing', 'Fujian', 'Guangdong', 'Guangxi', 'Guizhou',
            'Hainan', 'Hebei', 'Heilongjiang', 'Henan', 'Hubei', 'Hunan',
            'Inner Mongolia', 'Jiangsu', 'Jiangxi', 'Jilin', 'Liaoning',
            'Ningxia', 'Qinghai', 'Shaanxi', 'Shandong', 'Shanghai',
            'Sichuan', 'Tianjin', 'Tibet', 'Xinjiang', 'Yunnan', 'Zhejiang',
            'Unassigned (China)'
        ]

        # 航司分组
        self.airline_groups = {
            '国航系': [
                'Air China', 'Air China Cargo', 'Air China Inner Mongolia',
                'Beijing Airlines', 'Dalian Airlines', 'Shenzhen Airlines',
                'Shandong Airlines', 'Air Macau'
            ],
            '东航系': [
                'China Eastern Airlines', 'China Eastern Airlines Guangdong',
                'China Eastern Airlines Wuhan', 'China Eastern Airlines Yunnan',
                'Shanghai Airlines', 'China United Airlines', 'China Eastern Cargo'
            ],
            '南航系': [
                'China Southern Airlines', 'China Southern Cargo',
                'Chongqing Airlines', 'Hebei Airlines', 'Jiangxi Air',
                'Xiamen Airlines', 'Sichuan Airlines'
            ],
            '海航系': [
                'Hainan Airlines', 'Capital Airlines', 'Tianjin Airlines',
                'West Air', 'Lucky Air', 'GX Airlines', 'Fuzhou Airlines',
                '9 Air', 'Air Guilin', 'Grand China Air', 'Suparna Airlines',
                'Beijing Capital Airlines', 'Urumqi Air', 'Hong Kong Airlines'
            ],
            '地方航司': [
                'Juneyao Air', 'Spring Airlines', 'Chengdu Airlines',
                'Tibet Airlines', 'Loong Air', 'Ruili Airlines',
                'Qingdao Airlines', 'Okay Airways', 'Colorful Guizhou Airlines',
                'China Express Airlines', 'Joy Air', 'Donghai Airlines',
                'Kunming Airlines', 'LongJiang Airlines'
            ]
        }

        # 所有航司列表
        self.all_airlines = []
        for group_airlines in self.airline_groups.values():
            self.all_airlines.extend(group_airlines)

        # 数据存储
        self.df = None
        self.filtered_df = None

    def load_and_filter_data(self, file_path, status_filter=None, verbose=True):
        """加载和筛选数据"""
        if verbose:
            st.info(f"正在加载文件: {os.path.basename(file_path)}")

        try:
            # 读取Excel文件
            self.df = pd.read_excel(file_path)
            if verbose:
                st.success(f"✅ 原始数据行数: {len(self.df)}")

            # 数据清洗
            self._clean_data(verbose=verbose)

            # 筛选中国内地飞机
            self.filtered_df = self._filter_china_mainland(verbose=verbose)

            # 筛选窄体机
            self.filtered_df = self._filter_narrow_body(verbose=verbose)

            # 应用状态筛选
            if status_filter and status_filter != 'All Status':
                if 'Status' in self.filtered_df.columns:
                    self.filtered_df = self.filtered_df[self.filtered_df['Status'] == status_filter]
                    if verbose:
                        st.write(f"📊 状态筛选: {status_filter}")

            # 数据增强
            self._enhance_data(verbose=verbose)

            if verbose:
                st.success(f"✅ 数据加载完成!")
                st.write(f"  • 原始数据: {len(self.df)} 行")
                st.write(f"  • 筛选后数据: {len(self.filtered_df)} 行")

                # 显示数据概览
                self._display_data_overview()

            return True

        except Exception as e:
            if verbose:
                st.error(f"❌ 数据加载失败: {e}")
            return False

    def _clean_data(self, verbose=True):
        """数据清洗"""
        # 1. 处理机龄数据
        age_column = None
        for col in self.df.columns:
            if 'age' in str(col).lower() and 'stage' not in str(col).lower():
                age_column = col
                break

        if age_column:
            if verbose:
                st.write(f"📝 使用列 '{age_column}' 作为年龄列")
            self.df['Age'] = pd.to_numeric(self.df[age_column], errors='coerce')
            if verbose:
                st.write(f"  • 有效机龄数据: {self.df['Age'].notna().sum()} 行")

            # 处理异常机龄值
            age_mask = self.df['Age'] > 50
            if age_mask.any():
                if verbose:
                    st.warning(f"⚠️ 发现 {age_mask.sum()} 个异常机龄值 (>50年)")
                self.df.loc[age_mask, 'Age'] = np.nan
        else:
            if verbose:
                st.warning("⚠️ 未找到年龄列，将创建空Age列")
            self.df['Age'] = np.nan

        # 2. 处理状态数据
        if 'Status' in self.df.columns:
            # 标准化状态名称
            def normalize_status(status):
                if pd.isna(status):
                    return 'Unknown'

                status_str = str(status).strip()
                if status_str in ['In Service', 'Storage', 'Unknown']:
                    return status_str
                elif 'service' in status_str.lower() or 'in service' in status_str.lower():
                    return 'In Service'
                elif 'storage' in status_str.lower():
                    return 'Storage'
                else:
                    return status_str

            self.df['Status'] = self.df['Status'].apply(normalize_status)
            self.df['Status'] = self.df['Status'].fillna('Unknown')

        # 3. 移除重复记录
        if 'Registration' in self.df.columns:
            before = len(self.df)
            self.df = self.df.drop_duplicates(subset=['Registration'], keep='first')
            after = len(self.df)
            if before > after and verbose:
                st.write(f"  • 移除 {before - after} 个重复记录")

    def _filter_china_mainland(self, verbose=True):
        """筛选中国内地飞机"""
        if verbose:
            st.write("🌏 筛选中国内地飞机...")

        if len(self.df) == 0:
            return pd.DataFrame()

        mask = pd.Series(False, index=self.df.index)

        # 筛选Operator State
        if 'Operator State' in self.df.columns:
            for province in self.china_states:
                mask = mask | self.df['Operator State'].astype(str).str.contains(province, case=False, na=False)

        # 筛选Operator
        if 'Operator' in self.df.columns:
            china_operators = ['China', 'Air China', 'China Eastern', 'China Southern',
                               'Hainan', 'Shenzhen', 'Xiamen', 'Sichuan', 'Shanghai',
                               'Beijing', 'Guangzhou', 'Tianjin']
            for operator in china_operators:
                mask = mask | self.df['Operator'].astype(str).str.contains(operator, case=False, na=False)

        # 筛选Primary Usage为Passenger（如果存在该列）
        if 'Primary Usage' in self.df.columns:
            usage_mask = self.df['Primary Usage'] == 'Passenger'
            mask = mask & usage_mask

        filtered_df = self.df[mask].copy()
        if verbose:
            st.success(f"✅ 筛选结果: {len(filtered_df)} 架飞机")

        return filtered_df

    def _filter_narrow_body(self, verbose=True):
        """筛选窄体机"""
        if verbose:
            st.write("✈️ 筛选窄体机...")

        if self.filtered_df is None or len(self.filtered_df) == 0:
            return pd.DataFrame()

        # 标准化机型名称
        def normalize_model(model):
            if pd.isna(model) or model is None:
                return None

            model_str = str(model).strip().upper()

            # 检查是否是窄体机
            for standard_model in self.narrow_body_models:
                standard_model_upper = standard_model.upper()

                # 检查标准型号是否在型号字符串中
                if standard_model_upper in model_str:
                    # 特殊处理neo系列
                    if standard_model == 'A319neo':
                        if 'NEO' in model_str:
                            return 'A319neo'
                        elif 'A319' in model_str and 'NEO' not in model_str:
                            return 'A319'
                    elif standard_model == 'A320neo':
                        if 'NEO' in model_str or '-200N' in model_str:
                            return 'A320neo'
                        elif 'A320' in model_str and 'NEO' not in model_str and '-200N' not in model_str:
                            return 'A320'
                    elif standard_model == 'A321neo':
                        if 'NEO' in model_str or '-200N' in model_str or '-200NX' in model_str:
                            return 'A321neo'
                        elif 'A321' in model_str and 'NEO' not in model_str and '-200N' not in model_str and '-200NX' not in model_str:
                            return 'A321'
                    else:
                        return standard_model

            return None

        # 应用筛选
        model_filtered = self.filtered_df[self.filtered_df['Master Series'].apply(
            lambda x: normalize_model(x) in self.narrow_body_models if pd.notna(x) else False)]

        if verbose:
            st.success(f"✅ 窄体机筛选结果: {len(model_filtered)} 架飞机")

        return model_filtered

    def _enhance_data(self, verbose=True):
        """数据增强"""
        if verbose:
            st.write("🔧 增强数据...")

        if self.filtered_df is None or len(self.filtered_df) == 0:
            return

        # 1. 标准化制造商信息
        def get_manufacturer(name):
            if pd.isna(name):
                return 'Unknown'

            name_str = str(name).upper()

            for key, value in self.manufacturer_mapping.items():
                if key in name_str:
                    return value

            # 检查特定型号
            if '737' in name_str or '747' in name_str or '757' in name_str or '767' in name_str or '777' in name_str or '787' in name_str:
                return 'Boeing'
            elif 'A3' in name_str or 'A330' in name_str or 'A340' in name_str or 'A350' in name_str or 'A380' in name_str:
                return 'Airbus'
            elif 'E1' in name_str or 'E2' in name_str or 'ERJ' in name_str:
                return 'Embraer'
            elif 'ARJ' in name_str or 'C919' in name_str or 'COMAC' in name_str:
                return 'COMAC'
            elif 'CRJ' in name_str:
                return 'Bombardier'

            return 'Other'

        if 'Manufacturer' in self.filtered_df.columns:
            self.filtered_df['Manufacturer_Category'] = self.filtered_df['Manufacturer'].apply(get_manufacturer)
        elif 'Master Series' in self.filtered_df.columns:
            self.filtered_df['Manufacturer_Category'] = self.filtered_df['Master Series'].apply(get_manufacturer)
        else:
            self.filtered_df['Manufacturer_Category'] = 'Unknown'

        # 2. 估算座位数
        def estimate_seats(model):
            if pd.isna(model):
                return 150

            model_str = str(model).upper()

            for key, value in self.seat_capacity_map.items():
                if key.upper() in model_str:
                    return value

            # 基于型号前缀估算
            if '737-7' in model_str or '737-600' in model_str:
                return 130
            elif '737-8' in model_str:
                return 160
            elif '737-9' in model_str:
                return 180
            elif '737 MAX' in model_str:
                return 180
            elif 'A319' in model_str:
                return 124
            elif 'A320' in model_str:
                return 150
            elif 'A321' in model_str:
                return 185
            elif 'E190' in model_str:
                return 100
            elif 'E195' in model_str:
                return 120
            elif 'CRJ' in model_str:
                return 70
            elif 'ARJ' in model_str:
                return 90
            elif 'C919' in model_str:
                return 168

            return 150

        if 'Master Series' in self.filtered_df.columns:
            self.filtered_df['Estimated_Seats'] = self.filtered_df['Master Series'].apply(estimate_seats)
        else:
            self.filtered_df['Estimated_Seats'] = 150

        # 3. 座位等级分类
        def get_seat_category(seats):
            if seats < 100:
                return 'Under 100 seats'
            elif seats <= 150:
                return '100-150 seats'
            else:
                return 'Over 150 seats'

        self.filtered_df['Seat_Category'] = self.filtered_df['Estimated_Seats'].apply(get_seat_category)

        # 4. 机龄分类
        def get_age_category(age):
            if pd.isna(age):
                return 'Unknown'
            elif age < 5:
                return '<5 years'
            elif age < 10:
                return '5-10 years'
            elif age < 15:
                return '10-15 years'
            elif age < 20:
                return '15-20 years'
            else:
                return '≥20 years'

        if 'Age' in self.filtered_df.columns:
            self.filtered_df['Age_Category'] = self.filtered_df['Age'].apply(get_age_category)
        else:
            self.filtered_df['Age_Category'] = 'Unknown'

        # 5. 航司集团分类
        def get_airline_group(operator):
            if pd.isna(operator):
                return 'Other Airlines'

            operator_str = str(operator)

            for group, airlines in self.airline_groups.items():
                for airline in airlines:
                    if airline.lower() in operator_str.lower():
                        return group

            return 'Other Airlines'

        if 'Operator' in self.filtered_df.columns:
            self.filtered_df['Airline_Group'] = self.filtered_df['Operator'].apply(get_airline_group)
        else:
            self.filtered_df['Airline_Group'] = 'Other Airlines'

        # 6. 航司标准化
        def normalize_airline(operator):
            if pd.isna(operator):
                return 'Unknown'

            operator_str = str(operator).strip()

            # 移除括号内的内容
            operator_str = re.sub(r'\s*\([^)]*\)', '', operator_str).strip()

            # 查找匹配的航司
            for airline in self.all_airlines:
                if airline.lower() in operator_str.lower():
                    return airline

            return operator_str

        if 'Operator' in self.filtered_df.columns:
            self.filtered_df['Airline_Normalized'] = self.filtered_df['Operator'].apply(normalize_airline)

        if verbose:
            st.success("✅ 数据增强完成")

    def _display_data_overview(self):
        """显示数据概览"""
        if self.filtered_df is None or len(self.filtered_df) == 0:
            return

        st.markdown("---")
        st.subheader("📋 数据概览")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("总飞机数", len(self.filtered_df))

        with col2:
            if 'Airline_Normalized' in self.filtered_df.columns:
                airline_count = self.filtered_df['Airline_Normalized'].nunique()
                st.metric("航司数量", airline_count)

        with col3:
            if 'Manufacturer_Category' in self.filtered_df.columns:
                manufacturer_count = self.filtered_df['Manufacturer_Category'].nunique()
                st.metric("制造商数量", manufacturer_count)

        with col4:
            if 'Master Series' in self.filtered_df.columns:
                model_count = self.filtered_df['Master Series'].nunique()
                st.metric("机型数量", model_count)

        # 显示状态分布
        if 'Status' in self.filtered_df.columns:
            status_counts = self.filtered_df['Status'].value_counts()
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("状态分布")
                st.dataframe(status_counts)

            with col2:
                # 状态分布饼图 - 使用英文标题和标签
                fig, ax = plt.subplots(figsize=(8, 6))
                colors = ['#4CAF50', '#FF9800', '#9E9E9E']
                ax.pie(status_counts.values, labels=status_counts.index, autopct='%1.1f%%',
                       colors=colors[:len(status_counts)])
                ax.set_title('Aircraft Status Distribution', fontsize=14, fontweight='bold')
                st.pyplot(fig)

    def generate_airline_model_table(self, verbose=True):
        """生成航司x机型交叉表"""
        if verbose:
            st.write("📊 生成航司x机型交叉表...")

        if self.filtered_df is None or len(self.filtered_df) == 0:
            if verbose:
                st.warning("⚠️ 无数据可分析")
            return None

        # 创建交叉表
        if 'Airline_Normalized' in self.filtered_df.columns and 'Master Series' in self.filtered_df.columns:
            # 标准化机型名称
            def normalize_model_for_table(model):
                if pd.isna(model):
                    return 'Unknown'

                model_str = str(model).strip()

                # 简化机型名称
                if '737-700' in model_str:
                    return '737-700'
                elif '737-800' in model_str:
                    return '737-800'
                elif '737-900' in model_str:
                    return '737-900'
                elif '737 MAX' in model_str:
                    return '737 MAX'
                elif 'A319' in model_str and 'neo' not in model_str.lower():
                    return 'A319'
                elif 'A320' in model_str and 'neo' not in model_str.lower():
                    return 'A320'
                elif 'A321' in model_str and 'neo' not in model_str.lower():
                    return 'A321'
                elif 'A319neo' in model_str:
                    return 'A319neo'
                elif 'A320neo' in model_str:
                    return 'A320neo'
                elif 'A321neo' in model_str:
                    return 'A321neo'
                elif 'E190' in model_str:
                    return 'E190'
                elif 'E195' in model_str:
                    return 'E195'
                elif 'CRJ' in model_str:
                    return 'CRJ Series'
                elif 'ARJ21' in model_str:
                    return 'ARJ21'
                elif 'C919' in model_str:
                    return 'C919'
                else:
                    return model_str

            df_copy = self.filtered_df.copy()
            df_copy['Model_Normalized'] = df_copy['Master Series'].apply(normalize_model_for_table)

            # 创建交叉表
            cross_table = pd.crosstab(
                df_copy['Airline_Normalized'],
                df_copy['Model_Normalized'],
                margins=True,
                margins_name='Total'
            )

            # 按总数排序
            cross_table = cross_table.sort_values('Total', ascending=False)

            if verbose:
                st.success(f"✅ 交叉表生成完成: {cross_table.shape}")
            return cross_table

        return None

    def generate_airline_age_distribution(self, airline_name, verbose=True):
        """生成指定航司的机型x机龄分布表"""
        if verbose:
            st.write(f"📈 生成航司 {airline_name} 的机型x机龄分布表...")

        if self.filtered_df is None or len(self.filtered_df) == 0:
            if verbose:
                st.warning("⚠️ 无数据可分析")
            return None

        # 筛选指定航司
        if 'Airline_Normalized' in self.filtered_df.columns:
            airline_df = self.filtered_df[self.filtered_df['Airline_Normalized'] == airline_name].copy()
        else:
            airline_df = self.filtered_df[self.filtered_df['Operator'] == airline_name].copy()

        if len(airline_df) == 0:
            if verbose:
                st.warning(f"⚠️ 未找到航司: {airline_name}")
            return None

        # 标准化机型名称
        def normalize_model_for_table(model):
            if pd.isna(model):
                return 'Unknown'

            model_str = str(model).strip()

            # 简化机型名称
            if '737-700' in model_str:
                return '737-700'
            elif '737-800' in model_str:
                return '737-800'
            elif '737-900' in model_str:
                return '737-900'
            elif '737 MAX' in model_str:
                return '737 MAX'
            elif 'A319' in model_str and 'neo' not in model_str.lower():
                return 'A319'
            elif 'A320' in model_str and 'neo' not in model_str.lower():
                return 'A320'
            elif 'A321' in model_str and 'neo' not in model_str.lower():
                return 'A321'
            elif 'A319neo' in model_str:
                return 'A319neo'
            elif 'A320neo' in model_str:
                return 'A320neo'
            elif 'A321neo' in model_str:
                return 'A321neo'
            elif 'E190' in model_str:
                return 'E190'
            elif 'E195' in model_str:
                return 'E195'
            elif 'CRJ' in model_str:
                return 'CRJ Series'
            elif 'ARJ21' in model_str:
                return 'ARJ21'
            elif 'C919' in model_str:
                return 'C919'
            else:
                return model_str

        airline_df['Model_Normalized'] = airline_df['Master Series'].apply(normalize_model_for_table)

        # 计算机龄整数（向下取整）
        if 'Age' in airline_df.columns:
            airline_df['Age_Integer'] = airline_df['Age'].fillna(0).astype(int)
        else:
            airline_df['Age_Integer'] = 0

        # 创建机型x机龄交叉表
        age_table = pd.crosstab(
            airline_df['Model_Normalized'],
            airline_df['Age_Integer'],
            margins=True,
            margins_name='Total'
        )

        # 按总数排序
        age_table = age_table.sort_values('Total', ascending=False)

        if verbose:
            st.success(f"✅ 已生成 {airline_name} 的机龄分布: {len(airline_df)} 架飞机")
        return age_table

    def generate_airline_age_chart(self, airline_name):
        """生成单个航司的机龄分布图表"""
        if self.filtered_df is None or len(self.filtered_df) == 0:
            return None

        # 筛选航司数据
        if 'Airline_Normalized' in self.filtered_df.columns:
            airline_df = self.filtered_df[self.filtered_df['Airline_Normalized'] == airline_name].copy()
        else:
            airline_df = self.filtered_df[self.filtered_df['Operator'] == airline_name].copy()

        if len(airline_df) == 0:
            return None

        # 计算机龄分布
        if 'Age' in airline_df.columns:
            # 按机龄分类
            age_bins = [0, 5, 10, 15, 20, 100]
            age_labels = ['<5', '5-10', '10-15', '15-20', '≥20']
            airline_df['Age_Group'] = pd.cut(airline_df['Age'].fillna(0), bins=age_bins, labels=age_labels, right=False)

            age_distribution = airline_df['Age_Group'].value_counts().sort_index()

            # 生成机龄分布柱状图 - 使用英文标签
            fig, ax = plt.subplots(figsize=(12, 8))
            colors = ['#4ECDC4', '#45B7D1', '#FF6B6B', '#FFE66D', '#96CEB4']

            bars = ax.bar(age_distribution.index, age_distribution.values, color=colors[:len(age_distribution)])
            ax.set_xlabel('Age (years)', fontsize=14)
            ax.set_ylabel('Number of Aircraft', fontsize=14)
            ax.set_title(f'{airline_name} - Age Distribution', fontsize=18, fontweight='bold')

            # 添加数值标签
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width() / 2., height + 0.5,
                        f'{int(height)}', ha='center', va='bottom', fontsize=12)

            plt.tight_layout()
            return fig
        return None

    def generate_market_share_analysis(self, verbose=True):
        """生成市场占有率分析"""
        if verbose:
            st.write("📊 生成市场占有率分析...")

        if self.filtered_df is None or len(self.filtered_df) == 0:
            if verbose:
                st.warning("⚠️ 无数据可分析")
            return None

        analysis_results = {}

        # 1. 制造商市场占有率（所有窄体机）
        if 'Manufacturer_Category' in self.filtered_df.columns:
            manufacturer_counts = self.filtered_df['Manufacturer_Category'].value_counts()
            manufacturer_share = (manufacturer_counts / len(self.filtered_df) * 100).round(2)

            analysis_results['制造商全部'] = pd.DataFrame({
                '制造商': manufacturer_counts.index,
                '数量': manufacturer_counts.values,
                '占比 (%)': manufacturer_share.values
            })

        # 2. 按座位等级的制造商市场占有率
        if 'Manufacturer_Category' in self.filtered_df.columns and 'Seat_Category' in self.filtered_df.columns:
            seat_categories = ['Under 100 seats', '100-150 seats', 'Over 150 seats']

            for seat_cat in seat_categories:
                seat_df = self.filtered_df[self.filtered_df['Seat_Category'] == seat_cat]

                if len(seat_df) > 0:
                    manufacturer_counts = seat_df['Manufacturer_Category'].value_counts()
                    manufacturer_share = (manufacturer_counts / len(seat_df) * 100).round(2)

                    analysis_results[f'制造商 {seat_cat}'] = pd.DataFrame({
                        '制造商': manufacturer_counts.index,
                        '数量': manufacturer_counts.values,
                        '占比 (%)': manufacturer_share.values
                    })

        # 3. 机型市场占有率（所有窄体机）
        if 'Master Series' in self.filtered_df.columns:
            # 标准化机型名称
            def normalize_model_for_market_share(model):
                if pd.isna(model):
                    return 'Unknown'

                model_str = str(model).strip()

                # 简化机型名称
                if '737-700' in model_str:
                    return '737-700'
                elif '737-800' in model_str:
                    return '737-800'
                elif '737-900' in model_str:
                    return '737-900'
                elif '737 MAX' in model_str:
                    return '737 MAX'
                elif 'A319' in model_str and 'neo' not in model_str.lower():
                    return 'A319'
                elif 'A320' in model_str and 'neo' not in model_str.lower():
                    return 'A320'
                elif 'A321' in model_str and 'neo' not in model_str.lower():
                    return 'A321'
                elif 'A319neo' in model_str:
                    return 'A319neo'
                elif 'A320neo' in model_str:
                    return 'A320neo'
                elif 'A321neo' in model_str:
                    return 'A321neo'
                elif 'E190' in model_str:
                    return 'E190'
                elif 'E195' in model_str:
                    return 'E195'
                elif 'CRJ' in model_str:
                    return 'CRJ Series'
                elif 'ARJ21' in model_str:
                    return 'ARJ21'
                elif 'C919' in model_str:
                    return 'C919'
                else:
                    return model_str

            df_copy = self.filtered_df.copy()
            df_copy['Model_Normalized'] = df_copy['Master Series'].apply(normalize_model_for_market_share)

            model_counts = df_copy['Model_Normalized'].value_counts()
            model_share = (model_counts / len(df_copy) * 100).round(2)

            analysis_results['机型全部'] = pd.DataFrame({
                '机型': model_counts.index,
                '数量': model_counts.values,
                '占比 (%)': model_share.values
            })

        # 4. 按座位等级的机型市场占有率
        if 'Master Series' in self.filtered_df.columns and 'Seat_Category' in self.filtered_df.columns:
            seat_categories = ['Under 100 seats', '100-150 seats', 'Over 150 seats']

            for seat_cat in seat_categories:
                seat_df = self.filtered_df[self.filtered_df['Seat_Category'] == seat_cat].copy()

                if len(seat_df) > 0:
                    seat_df['Model_Normalized'] = seat_df['Master Series'].apply(normalize_model_for_market_share)

                    model_counts = seat_df['Model_Normalized'].value_counts()
                    model_share = (model_counts / len(seat_df) * 100).round(2)

                    analysis_results[f'机型 {seat_cat}'] = pd.DataFrame({
                        '机型': model_counts.index,
                        '数量': model_counts.values,
                        '占比 (%)': model_share.values
                    })

        if verbose:
            st.success("✅ 市场占有率分析完成")
        return analysis_results

    def generate_market_share_charts(self):
        """生成市场占有率图表"""
        charts = {}

        if self.filtered_df is None or len(self.filtered_df) == 0:
            return charts

        # 首先获取市场占有率分析结果
        market_share_data = self.generate_market_share_analysis(verbose=False)

        if not market_share_data:
            return charts

        # 为每个分析表生成饼图
        for chart_name, df in market_share_data.items():
            if df is None or len(df) == 0:
                continue

            # 简化图表标题
            chart_title = chart_name
            if chart_name == "制造商全部":
                chart_title = "Manufacturer Market Share (All Narrow-body)"
            elif "制造商 Under 100 seats" in chart_name:
                chart_title = "Manufacturer Market Share (Under 100 seats)"
            elif "制造商 100-150 seats" in chart_name:
                chart_title = "Manufacturer Market Share (100-150 seats)"
            elif "制造商 Over 150 seats" in chart_name:
                chart_title = "Manufacturer Market Share (Over 150 seats)"
            elif chart_name == "机型全部":
                chart_title = "Model Market Share (All Narrow-body)"
            elif "机型 Under 100 seats" in chart_name:
                chart_title = "Model Market Share (Under 100 seats)"
            elif "机型 100-150 seats" in chart_name:
                chart_title = "Model Market Share (100-150 seats)"
            elif "机型 Over 150 seats" in chart_name:
                chart_title = "Model Market Share (Over 150 seats)"

            # 确保数据列存在
            if len(df.columns) >= 2:
                # 第一列是分类（制造商或机型），第二列是数量
                category_col = df.columns[0]
                count_col = df.columns[1] if len(df.columns) > 1 else '数量'

                # 提取数据
                labels = df[category_col].astype(str).tolist()
                sizes = df[count_col].astype(float).tolist()

                # 创建饼图
                fig, ax = plt.subplots(figsize=(12, 9))

                # 限制显示的项目数量，合并小项目为"其他"
                if len(labels) > 8:
                    # 按大小排序
                    data = list(zip(labels, sizes))
                    data.sort(key=lambda x: x[1], reverse=True)

                    top_labels = [x[0] for x in data[:7]]
                    top_sizes = [x[1] for x in data[:7]]

                    other_size = sum([x[1] for x in data[7:]])
                    if other_size > 0:
                        top_labels.append("Other")
                        top_sizes.append(other_size)

                    labels = top_labels
                    sizes = top_sizes

                # 生成颜色
                colors = plt.cm.Set3(np.linspace(0, 1, len(labels)))

                # 创建饼图
                wedges, texts, autotexts = ax.pie(sizes, labels=labels, autopct='%1.1f%%',
                                                  colors=colors, startangle=90,
                                                  textprops={'fontsize': 10})

                # 设置标题
                ax.set_title(chart_title, fontsize=16, fontweight='bold', pad=20)

                # 美化百分比文本
                for autotext in autotexts:
                    autotext.set_color('black')
                    autotext.set_fontsize(11)
                    autotext.set_fontweight('bold')

                # 添加图例
                ax.legend(wedges, labels, title="Categories",
                          loc="center left", bbox_to_anchor=(1, 0, 0.5, 1),
                          fontsize=10)

                # 确保饼图是圆形
                ax.axis('equal')

                plt.tight_layout()

                # 保存图表
                charts[chart_name] = fig
                plt.close(fig)

        # 如果没有生成任何图表，回退到原有的两个图表
        if not charts:
            charts = self._generate_default_market_share_charts()

        return charts

    def _generate_default_market_share_charts(self):
        """生成默认的市场占有率图表（原有的两个图表）"""
        charts = {}

        # 1. 制造商市场份额饼图（所有窄体机）
        if 'Manufacturer_Category' in self.filtered_df.columns:
            manufacturer_counts = self.filtered_df['Manufacturer_Category'].value_counts()

            fig, ax = plt.subplots(figsize=(12, 10))
            colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFE66D', '#96CEB4', '#DDA0DD']

            # 只显示主要制造商
            main_manufacturers = manufacturer_counts.head(6)
            other_count = manufacturer_counts.sum() - main_manufacturers.sum()

            if other_count > 0:
                main_manufacturers = pd.concat([main_manufacturers, pd.Series([other_count], index=['Other'])])

            ax.pie(main_manufacturers.values, labels=main_manufacturers.index,
                   autopct='%1.1f%%', colors=colors[:len(main_manufacturers)], textprops={'fontsize': 12})
            ax.set_title('Manufacturer Market Share (Narrow-body Aircraft)', fontsize=18, fontweight='bold')

            charts['manufacturer_market_share'] = fig
            plt.close()

        # 2. 机型市场占有率饼图（所有窄体机，前10个机型）
        if 'Master Series' in self.filtered_df.columns:
            # 标准化机型名称
            def normalize_model_for_chart(model):
                if pd.isna(model):
                    return 'Unknown'

                model_str = str(model).strip()

                # 简化机型名称
                if '737-800' in model_str:
                    return '737-800'
                elif 'A320' in model_str and 'neo' not in model_str.lower():
                    return 'A320'
                elif 'A321' in model_str and 'neo' not in model_str.lower():
                    return 'A321'
                elif '737-700' in model_str:
                    return '737-700'
                elif 'A319' in model_str and 'neo' not in model_str.lower():
                    return 'A319'
                elif 'A320neo' in model_str:
                    return 'A320neo'
                elif '737 MAX' in model_str:
                    return '737 MAX'
                elif 'A321neo' in model_str:
                    return 'A321neo'
                elif 'E190' in model_str:
                    return 'E190'
                elif 'A319neo' in model_str:
                    return 'A319neo'
                elif 'E195' in model_str:
                    return 'E195'
                elif 'CRJ' in model_str:
                    return 'CRJ Series'
                elif 'ARJ21' in model_str:
                    return 'ARJ21'
                elif 'C919' in model_str:
                    return 'C919'
                else:
                    return 'Other'

            df_copy = self.filtered_df.copy()
            df_copy['Model_Normalized'] = df_copy['Master Series'].apply(normalize_model_for_chart)

            model_counts = df_copy['Model_Normalized'].value_counts()

            fig, ax = plt.subplots(figsize=(14, 10))
            colors = plt.cm.Set3(np.linspace(0, 1, len(model_counts.head(10))))

            # 显示前10个机型
            top_models = model_counts.head(10)
            other_count = model_counts.sum() - top_models.sum()

            if other_count > 0:
                top_models = pd.concat([top_models, pd.Series([other_count], index=['Other'])])

            ax.pie(top_models.values, labels=top_models.index,
                   autopct='%1.1f%%', colors=colors[:len(top_models)], textprops={'fontsize': 12})
            ax.set_title('Model Market Share (Top 10, Narrow-body Aircraft)', fontsize=18, fontweight='bold')

            charts['model_market_share'] = fig
            plt.close()

        return charts

    def generate_model_list(self, verbose=True):
        """生成机型列表"""
        if self.filtered_df is None or len(self.filtered_df) == 0:
            return None

        if 'Master Series' in self.filtered_df.columns:
            # 获取所有机型
            all_models = self.filtered_df['Master Series'].dropna().unique()

            # 标准化机型名称
            def normalize_model_for_list(model):
                if pd.isna(model):
                    return 'Unknown'

                model_str = str(model).strip()

                # 简化机型名称
                if '737-700' in model_str:
                    return '737-700'
                elif '737-800' in model_str:
                    return '737-800'
                elif '737-900' in model_str:
                    return '737-900'
                elif '737 MAX' in model_str:
                    return '737 MAX'
                elif 'A319' in model_str and 'neo' not in model_str.lower():
                    return 'A319'
                elif 'A320' in model_str and 'neo' not in model_str.lower():
                    return 'A320'
                elif 'A321' in model_str and 'neo' not in model_str.lower():
                    return 'A321'
                elif 'A319neo' in model_str:
                    return 'A319neo'
                elif 'A320neo' in model_str:
                    return 'A320neo'
                elif 'A321neo' in model_str:
                    return 'A321neo'
                elif 'E190' in model_str:
                    return 'E190'
                elif 'E195' in model_str:
                    return 'E195'
                elif 'CRJ' in model_str:
                    return 'CRJ Series'
                elif 'ARJ21' in model_str:
                    return 'ARJ21'
                elif 'C919' in model_str:
                    return 'C919'
                else:
                    return model_str

            # 统计每个机型的数量
            model_stats = []
            for model in sorted(all_models):
                model_count = len(self.filtered_df[self.filtered_df['Master Series'] == model])
                normalized_model = normalize_model_for_list(model)
                model_stats.append({
                    '原始机型': model,
                    '标准化机型': normalized_model,
                    '数量': model_count,
                    '占比 (%)': round(model_count / len(self.filtered_df) * 100, 2) if len(self.filtered_df) > 0 else 0
                })

            model_list_df = pd.DataFrame(model_stats)
            model_list_df = model_list_df.sort_values('数量', ascending=False)

            if verbose:
                st.write(f"📋 已生成机型列表，包含 {len(model_list_df)} 个机型")
            return model_list_df

        return None

    def export_airline_analysis(self, selected_airlines):
        """导出航司机龄分布分析到Excel"""
        st.write("💾 正在导出航司机龄分布分析到Excel...")

        # 创建一个进度容器
        progress_container = st.container()
        with progress_container:
            progress_bar = st.progress(0)
            status_text = st.empty()

            try:
                # 创建Excel写入器
                output = BytesIO()

                # 计算总步骤数
                # 固定步骤：数据信息、机型列表、航司x机型、航司汇总、制造商详情、机型详情 = 6步
                # 每个航司的处理步骤：1步
                fixed_steps = 6
                variable_steps = len(selected_airlines) if selected_airlines else 0
                total_steps = fixed_steps + variable_steps

                if total_steps == 0:
                    total_steps = 1  # 避免除零错误

                current_step = 0

                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    # 步骤1: 数据说明
                    current_step += 1
                    progress_value = min(current_step / total_steps, 1.0)  # 确保不超过1.0
                    progress_bar.progress(progress_value)
                    status_text.text(f"步骤 {current_step}/{total_steps}: 创建数据信息...")

                    info_data = {
                        '项目': [
                            '分析日期',
                            '数据文件',
                            '分析状态',
                            '总飞机数',
                            '航司数量',
                            '机型数量',
                            '机型列表'
                        ],
                        '值': [
                            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            '用户选择文件',
                            '窄体机（含支线机）',
                            len(self.filtered_df) if self.filtered_df is not None else 0,
                            len(self.filtered_df['Airline_Normalized'].unique()) if self.filtered_df is not None else 0,
                            len(self.filtered_df['Master Series'].unique()) if self.filtered_df is not None else 0,
                            ''  # 稍后更新
                        ]
                    }

                    info_df = pd.DataFrame(info_data)
                    info_df.to_excel(writer, sheet_name='数据信息', index=False)

                    # 步骤2: 机型列表
                    current_step += 1
                    progress_value = min(current_step / total_steps, 1.0)
                    progress_bar.progress(progress_value)
                    status_text.text(f"步骤 {current_step}/{total_steps}: 创建机型列表...")

                    model_list_df = self.generate_model_list(verbose=False)
                    if model_list_df is not None:
                        model_list_df.to_excel(writer, sheet_name='机型列表', index=False)

                        # 在数据信息中更新机型列表信息
                        # 获取前10个最常见的机型
                        top_models = model_list_df.nlargest(10, '数量')
                        model_names = top_models['标准化机型'].tolist()
                        model_counts = top_models['数量'].tolist()

                        model_list_str = f"前10个机型: " + ", ".join(
                            [f"{name}({count})" for name, count in zip(model_names, model_counts)])

                        # 更新数据信息中的机型列表
                        info_df.loc[info_df['项目'] == '机型列表', '值'] = model_list_str
                        writer.book.remove(writer.book['数据信息'])
                        info_df.to_excel(writer, sheet_name='数据信息', index=False)

                    # 步骤3: 航司x机型交叉表
                    current_step += 1
                    progress_value = min(current_step / total_steps, 1.0)
                    progress_bar.progress(progress_value)
                    status_text.text(f"步骤 {current_step}/{total_steps}: 创建航司x机型表...")

                    airline_model_table = self.generate_airline_model_table(verbose=False)
                    if airline_model_table is not None:
                        airline_model_table.to_excel(writer, sheet_name='航司x机型')

                    # 步骤4: 每个选中的航司的机型x机龄分布表
                    if selected_airlines:
                        for i, airline in enumerate(selected_airlines):
                            current_step += 1
                            progress_value = min(current_step / total_steps, 1.0)
                            progress_bar.progress(progress_value)
                            status_text.text(
                                f"步骤 {current_step}/{total_steps}: 处理航司 {airline} ({i + 1}/{len(selected_airlines)})...")

                            airline_age_table = self.generate_airline_age_distribution(airline, verbose=False)
                            if airline_age_table is not None:
                                # 简化sheet名称（Excel限制31个字符）
                                safe_sheet_name = airline[:28].replace('/', '_').replace('\\', '_').replace(':', '_')
                                if len(safe_sheet_name) < 4:
                                    safe_sheet_name = f"航司_{airline[:20]}"
                                airline_age_table.to_excel(writer, sheet_name=safe_sheet_name)

                    # 步骤5: 航司汇总信息
                    current_step += 1
                    progress_value = min(current_step / total_steps, 1.0)
                    progress_bar.progress(progress_value)
                    status_text.text(f"步骤 {current_step}/{total_steps}: 创建航司汇总...")

                    if selected_airlines:
                        summary_data = []
                        for airline in selected_airlines:
                            if 'Airline_Normalized' in self.filtered_df.columns:
                                airline_df = self.filtered_df[self.filtered_df['Airline_Normalized'] == airline].copy()
                            else:
                                airline_df = self.filtered_df[self.filtered_df['Operator'] == airline].copy()

                            if len(airline_df) > 0:
                                total_aircraft = len(airline_df)
                                avg_age = airline_df['Age'].mean() if 'Age' in airline_df.columns else 0
                                model_count = airline_df[
                                    'Master Series'].nunique() if 'Master Series' in airline_df.columns else 0

                                summary_data.append({
                                    '航司': airline,
                                    '总飞机数': total_aircraft,
                                    '平均机龄': round(avg_age, 1),
                                    '机型数量': model_count
                                })

                        if summary_data:
                            summary_df = pd.DataFrame(summary_data)
                            summary_df.to_excel(writer, sheet_name='航司汇总', index=False)

                    # 步骤6: 制造商详细数据
                    current_step += 1
                    progress_value = min(current_step / total_steps, 1.0)
                    progress_bar.progress(progress_value)
                    status_text.text(f"步骤 {current_step}/{total_steps}: 创建制造商详情...")

                    if 'Manufacturer_Category' in self.filtered_df.columns:
                        manufacturer_summary = self.filtered_df.groupby('Manufacturer_Category').agg({
                            'Registration': 'count',
                            'Age': 'mean',
                            'Estimated_Seats': 'mean'
                        }).rename(columns={'Registration': '数量', 'Age': '平均机龄', 'Estimated_Seats': '平均座位数'})
                        manufacturer_summary['平均机龄'] = manufacturer_summary['平均机龄'].round(1)
                        manufacturer_summary['平均座位数'] = manufacturer_summary['平均座位数'].round(0)
                        manufacturer_summary = manufacturer_summary.sort_values('数量', ascending=False)
                        manufacturer_summary.to_excel(writer, sheet_name='制造商详情')

                    # 步骤7: 机型详细数据
                    current_step += 1
                    progress_value = min(current_step / total_steps, 1.0)
                    progress_bar.progress(progress_value)
                    status_text.text(f"步骤 {current_step}/{total_steps}: 创建机型详情...")

                    if 'Master Series' in self.filtered_df.columns:
                        # 标准化机型名称
                        def normalize_model_for_market_share(model):
                            if pd.isna(model):
                                return 'Unknown'

                            model_str = str(model).strip()

                            # 简化机型名称
                            if '737-700' in model_str:
                                return '737-700'
                            elif '737-800' in model_str:
                                return '737-800'
                            elif '737-900' in model_str:
                                return '737-900'
                            elif '737 MAX' in model_str:
                                return '737 MAX'
                            elif 'A319' in model_str and 'neo' not in model_str.lower():
                                return 'A319'
                            elif 'A320' in model_str and 'neo' not in model_str.lower():
                                return 'A320'
                            elif 'A321' in model_str and 'neo' not in model_str.lower():
                                return 'A321'
                            elif 'A319neo' in model_str:
                                return 'A319neo'
                            elif 'A320neo' in model_str:
                                return 'A320neo'
                            elif 'A321neo' in model_str:
                                return 'A321neo'
                            elif 'E190' in model_str:
                                return 'E190'
                            elif 'E195' in model_str:
                                return 'E195'
                            elif 'CRJ' in model_str:
                                return 'CRJ Series'
                            elif 'ARJ21' in model_str:
                                return 'ARJ21'
                            elif 'C919' in model_str:
                                return 'C919'
                            else:
                                return model_str

                        df_copy = self.filtered_df.copy()
                        df_copy['Model_Normalized'] = df_copy['Master Series'].apply(normalize_model_for_market_share)

                        model_summary = df_copy.groupby('Model_Normalized').agg({
                            'Registration': 'count',
                            'Age': 'mean',
                            'Estimated_Seats': 'mean'
                        }).rename(columns={'Registration': '数量', 'Age': '平均机龄', 'Estimated_Seats': '平均座位数'})
                        model_summary['平均机龄'] = model_summary['平均机龄'].round(1)
                        model_summary['平均座位数'] = model_summary['平均座位数'].round(0)
                        model_summary = model_summary.sort_values('数量', ascending=False)
                        model_summary.to_excel(writer, sheet_name='机型详情')

                output.seek(0)

                # 完成进度条
                progress_bar.progress(1.0)
                status_text.text("✅ Excel文件生成成功!")

                # 稍等一下，让用户看到完成状态
                import time
                time.sleep(0.5)

                # 清空进度容器
                progress_container.empty()

                # 显示下载按钮
                st.success("✅ Excel文件已准备好下载")
                st.download_button(
                    label="📥 下载航司分析结果",
                    data=output,
                    file_name=f"航司机龄分析_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    key="download_airline_btn"
                )
                return output

            except Exception as e:
                progress_container.empty()
                st.error(f"❌ 导出Excel失败: {e}")
                import traceback
                st.code(traceback.format_exc())
                return None

    def export_market_share_analysis(self):
        """导出市场占有率分析到Excel"""
        st.write("💾 正在导出市场占有率分析到Excel...")

        # 创建一个进度容器
        progress_container = st.container()
        with progress_container:
            progress_bar = st.progress(0)
            status_text = st.empty()

            try:
                # 创建Excel写入器
                output = BytesIO()

                # 固定步骤数
                total_steps = 7
                current_step = 0

                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    # 步骤1: 数据说明
                    current_step += 1
                    progress_value = min(current_step / total_steps, 1.0)
                    progress_bar.progress(progress_value)
                    status_text.text(f"步骤 {current_step}/{total_steps}: 创建数据信息...")

                    info_data = {
                        '项目': [
                            '分析日期',
                            '数据文件',
                            '分析状态',
                            '总飞机数',
                            '航司数量',
                            '机型数量',
                            '机型列表'
                        ],
                        '值': [
                            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            '用户选择文件',
                            '窄体机（含支线机）',
                            len(self.filtered_df) if self.filtered_df is not None else 0,
                            len(self.filtered_df['Airline_Normalized'].unique()) if self.filtered_df is not None else 0,
                            len(self.filtered_df['Master Series'].unique()) if self.filtered_df is not None else 0,
                            ''  # 稍后更新
                        ]
                    }

                    info_df = pd.DataFrame(info_data)
                    info_df.to_excel(writer, sheet_name='数据信息', index=False)

                    # 步骤2: 机型列表
                    current_step += 1
                    progress_value = min(current_step / total_steps, 1.0)
                    progress_bar.progress(progress_value)
                    status_text.text(f"步骤 {current_step}/{total_steps}: 创建机型列表...")

                    model_list_df = self.generate_model_list(verbose=False)
                    if model_list_df is not None:
                        model_list_df.to_excel(writer, sheet_name='机型列表', index=False)

                        # 在数据信息中更新机型列表信息
                        # 获取前10个最常见的机型
                        top_models = model_list_df.nlargest(10, '数量')
                        model_names = top_models['标准化机型'].tolist()
                        model_counts = top_models['数量'].tolist()

                        model_list_str = f"前10个机型: " + ", ".join(
                            [f"{name}({count})" for name, count in zip(model_names, model_counts)])

                        # 更新数据信息中的机型列表
                        info_df.loc[info_df['项目'] == '机型列表', '值'] = model_list_str
                        writer.book.remove(writer.book['数据信息'])
                        info_df.to_excel(writer, sheet_name='数据信息', index=False)

                    # 步骤3: 市场占有率分析
                    current_step += 1
                    progress_value = min(current_step / total_steps, 1.0)
                    progress_bar.progress(progress_value)
                    status_text.text(f"步骤 {current_step}/{total_steps}: 创建市场占有率分析...")

                    market_share = self.generate_market_share_analysis(verbose=False)
                    if market_share:
                        for sheet_name, df in market_share.items():
                            safe_sheet_name = sheet_name[:31]
                            df.to_excel(writer, sheet_name=safe_sheet_name, index=False)

                    # 步骤4: 制造商详细数据
                    current_step += 1
                    progress_value = min(current_step / total_steps, 1.0)
                    progress_bar.progress(progress_value)
                    status_text.text(f"步骤 {current_step}/{total_steps}: 创建制造商详情...")

                    if 'Manufacturer_Category' in self.filtered_df.columns:
                        manufacturer_summary = self.filtered_df.groupby('Manufacturer_Category').agg({
                            'Registration': 'count',
                            'Age': 'mean',
                            'Estimated_Seats': 'mean'
                        }).rename(columns={'Registration': '数量', 'Age': '平均机龄', 'Estimated_Seats': '平均座位数'})
                        manufacturer_summary['平均机龄'] = manufacturer_summary['平均机龄'].round(1)
                        manufacturer_summary['平均座位数'] = manufacturer_summary['平均座位数'].round(0)
                        manufacturer_summary = manufacturer_summary.sort_values('数量', ascending=False)
                        manufacturer_summary.to_excel(writer, sheet_name='制造商详情')

                    # 步骤5: 机型详细数据
                    current_step += 1
                    progress_value = min(current_step / total_steps, 1.0)
                    progress_bar.progress(progress_value)
                    status_text.text(f"步骤 {current_step}/{total_steps}: 创建机型详情...")

                    if 'Master Series' in self.filtered_df.columns:
                        # 标准化机型名称
                        def normalize_model_for_market_share(model):
                            if pd.isna(model):
                                return 'Unknown'

                            model_str = str(model).strip()

                            # 简化机型名称
                            if '737-700' in model_str:
                                return '737-700'
                            elif '737-800' in model_str:
                                return '737-800'
                            elif '737-900' in model_str:
                                return '737-900'
                            elif '737 MAX' in model_str:
                                return '737 MAX'
                            elif 'A319' in model_str and 'neo' not in model_str.lower():
                                return 'A319'
                            elif 'A320' in model_str and 'neo' not in model_str.lower():
                                return 'A320'
                            elif 'A321' in model_str and 'neo' not in model_str.lower():
                                return 'A321'
                            elif 'A319neo' in model_str:
                                return 'A319neo'
                            elif 'A320neo' in model_str:
                                return 'A320neo'
                            elif 'A321neo' in model_str:
                                return 'A321neo'
                            elif 'E190' in model_str:
                                return 'E190'
                            elif 'E195' in model_str:
                                return 'E195'
                            elif 'CRJ' in model_str:
                                return 'CRJ Series'
                            elif 'ARJ21' in model_str:
                                return 'ARJ21'
                            elif 'C919' in model_str:
                                return 'C919'
                            else:
                                return model_str

                        df_copy = self.filtered_df.copy()
                        df_copy['Model_Normalized'] = df_copy['Master Series'].apply(normalize_model_for_market_share)

                        model_summary = df_copy.groupby('Model_Normalized').agg({
                            'Registration': 'count',
                            'Age': 'mean',
                            'Estimated_Seats': 'mean'
                        }).rename(columns={'Registration': '数量', 'Age': '平均机龄', 'Estimated_Seats': '平均座位数'})
                        model_summary['平均机龄'] = model_summary['平均机龄'].round(1)
                        model_summary['平均座位数'] = model_summary['平均座位数'].round(0)
                        model_summary = model_summary.sort_values('数量', ascending=False)
                        model_summary.to_excel(writer, sheet_name='机型详情')

                output.seek(0)

                # 完成进度条
                progress_bar.progress(1.0)
                status_text.text("✅ Excel文件生成成功!")

                # 稍等一下，让用户看到完成状态
                import time
                time.sleep(0.5)

                # 清空进度容器
                progress_container.empty()

                # 显示下载按钮
                st.success("✅ Excel文件已准备好下载")
                st.download_button(
                    label="📥 下载市场分析结果",
                    data=output,
                    file_name=f"市场占有率分析_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    key="download_market_btn"
                )
                return output

            except Exception as e:
                progress_container.empty()
                st.error(f"❌ 导出Excel失败: {e}")
                import traceback
                st.code(traceback.format_exc())
                return None


def main():
    # 页面配置
    st.set_page_config(
        page_title="中国窄体机机龄分布与市场占有率分析工具",
        page_icon="✈️",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # 自定义CSS
    st.markdown("""
    <style>
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    .stDataFrame {
        width: 100%;
    }
    .stButton > button {
        width: 100%;
        margin-top: 10px;
    }
    .stSelectbox, .stMultiselect {
        width: 100%;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #f0f2f6;
        border-radius: 4px 4px 0px 0px;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #4CAF50;
        color: white;
    }
    .stProgress > div > div > div > div {
        background-color: #4CAF50;
    }
    </style>
    """, unsafe_allow_html=True)

    # 标题
    st.title("✈️ 中国窄体机机龄分布与市场占有率分析工具")
    st.markdown("---")

    # 初始化分析工具
    if 'analyzer' not in st.session_state:
        st.session_state.analyzer = ChinaAircraftAnalysisTool()
        st.session_state.selected_airlines = []

    # 侧边栏
    with st.sidebar:
        st.header("📁 文件设置")

        # 文件上传
        uploaded_file = st.file_uploader("上传数据文件", type=['xlsx', 'xls'], help="上传包含飞机数据的Excel文件")

        if uploaded_file is not None:
            # 保存上传的文件到临时位置
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
            temp_file.write(uploaded_file.getbuffer())
            temp_file_path = temp_file.name
            temp_file.close()

            # 状态筛选
            status_filter = st.selectbox(
                "状态筛选",
                options=['All Status', 'In Service', 'Storage'],
                index=0
            )

            # 加载数据按钮
            if st.button("加载数据", type="primary", use_container_width=True, key="load_data_btn"):
                with st.spinner("正在加载和筛选数据..."):
                    success = st.session_state.analyzer.load_and_filter_data(temp_file_path, status_filter)
                    if success:
                        st.session_state.file_loaded = True
                        # 重置航司选择
                        st.session_state.selected_airlines = []

                        # 清理临时文件
                        import os
                        os.unlink(temp_file_path)

        st.markdown("---")
        st.info("""
        **使用说明:**
        1. 上传数据文件 (如: AircraftDetail221225.xlsx)
        2. 选择状态筛选
        3. 点击"加载数据"
        4. 在主页面选择分析类型
        5. 执行分析并查看结果

        **支持的数据格式:**
        - 包含飞机数据的Excel文件
        - 应包含字段: Registration, Operator, Master Series, Manufacturer, Age, Status
        """)

    # 主内容区域
    if hasattr(st.session_state, 'file_loaded') and st.session_state.analyzer.filtered_df is not None:
        analyzer = st.session_state.analyzer

        # 创建标签页 - 移除侧边栏的分析类型选择，改用标签页
        tab1, tab2 = st.tabs(["✈️ 航司机龄分布分析", "📊 市场占有率分析"])

        with tab1:
            st.header("航司机龄分布分析")

            # 初始化 selected_airlines
            if 'selected_airlines' not in st.session_state:
                st.session_state.selected_airlines = []

            # 航司选择
            if 'Airline_Normalized' in analyzer.filtered_df.columns:
                airlines = sorted(analyzer.filtered_df['Airline_Normalized'].unique().tolist())

                # 回调函数定义
                def select_all_callback():
                    st.session_state.selected_airlines = airlines.copy()

                def clear_all_callback():
                    st.session_state.selected_airlines = []

                col1, col2 = st.columns([3, 1])

                with col1:
                    # 航司多选框
                    selected_airlines = st.multiselect(
                        "选择航司 (可多选)",
                        options=airlines,
                        default=st.session_state.selected_airlines,
                        key="airline_selector"
                    )

                    # 更新 session state
                    if selected_airlines != st.session_state.selected_airlines:
                        st.session_state.selected_airlines = selected_airlines

                with col2:
                    st.write("")
                    st.write("")
                    col_select, col_clear = st.columns(2)

                    with col_select:
                        if st.button("全选航司",
                                     key="select_all_btn",
                                     on_click=select_all_callback,
                                     use_container_width=True):
                            pass  # 回调函数已经处理

                    with col_clear:
                        if st.button("清空选择",
                                     key="clear_all_btn",
                                     on_click=clear_all_callback,
                                     use_container_width=True):
                            pass  # 回调函数已经处理

                # 显示选择状态
                if st.session_state.selected_airlines:
                    st.success(f"✅ 已选择 {len(st.session_state.selected_airlines)} 个航司")

                    # 三个主要功能按钮
                    st.markdown("---")
                    st.subheader("分析功能")

                    col_btn1, col_btn2, col_btn3 = st.columns(3)

                    with col_btn1:
                        if st.button("📋 生成航司x机型表", type="primary", use_container_width=True,
                                     key="cross_table_btn"):
                            with st.spinner("正在生成交叉表..."):
                                cross_table = analyzer.generate_airline_model_table()
                                if cross_table is not None:
                                    st.markdown("### 航司x机型交叉表")
                                    st.dataframe(cross_table.style.background_gradient(cmap='Blues'),
                                                 use_container_width=True)

                    with col_btn2:
                        if st.button("📈 生成机龄分布图", type="primary", use_container_width=True,
                                     key="age_charts_btn"):
                            if st.session_state.selected_airlines:
                                st.markdown("### 机龄分布图表")
                                for i in range(0, len(st.session_state.selected_airlines), 3):
                                    cols = st.columns(3)
                                    for j in range(3):
                                        if i + j < len(st.session_state.selected_airlines):
                                            airline = st.session_state.selected_airlines[i + j]
                                            with cols[j]:
                                                st.markdown(f"**{airline}**")
                                                fig = analyzer.generate_airline_age_chart(airline)
                                                if fig is not None:
                                                    st.pyplot(fig)

                    with col_btn3:
                        if st.button("💾 导出到Excel", type="primary", use_container_width=True,
                                     key="export_airline_btn"):
                            excel_data = analyzer.export_airline_analysis(st.session_state.selected_airlines)

                    # 显示各航司机型x机龄表
                    st.markdown("---")
                    st.subheader("各航司机型x机龄分布")

                    for airline in st.session_state.selected_airlines:
                        with st.expander(f"📊 {airline} - 机型x机龄分布", expanded=False):
                            age_table = analyzer.generate_airline_age_distribution(airline)
                            if age_table is not None:
                                st.dataframe(age_table.style.background_gradient(cmap='YlOrRd'),
                                             use_container_width=True)
                else:
                    st.warning("⚠️ 请至少选择一个航司进行分析")

                    # 显示可选航司数量
                    st.info(f"📋 当前数据中有 {len(airlines)} 个航司可供选择")

                    # 快速选择提示
                    if st.button("点此快速选择前5个航司", key="quick_select_btn"):
                        st.session_state.selected_airlines = airlines[:5]
                        st.rerun()
            else:
                st.warning("⚠️ 数据中没有找到航司信息")

        with tab2:
            st.header("市场占有率分析")

            # 创建分析功能区
            st.markdown("---")
            st.subheader("分析功能")

            col1, col2, col3 = st.columns(3)

            with col1:
                if st.button("📊 生成市场占有率表", type="primary", use_container_width=True, key="market_table_btn"):
                    with st.spinner("正在生成市场占有率分析..."):
                        market_share = analyzer.generate_market_share_analysis()
                        if market_share:
                            for name, df in market_share.items():
                                st.markdown(f"### {name}")
                                st.dataframe(df.style.background_gradient(cmap='Greens'), use_container_width=True)

            with col2:
                if st.button("📈 生成市场占有率图", type="primary", use_container_width=True, key="market_charts_btn"):
                    st.markdown("### 市场占有率图表")

                    # 获取市场占有率分析数据
                    market_share_data = analyzer.generate_market_share_analysis(verbose=False)

                    # 生成对应的图表
                    charts = analyzer.generate_market_share_charts()

                    if charts:
                        # 使用标签页或可折叠区域来组织多个图表
                        tab_names = list(charts.keys())
                        if len(tab_names) <= 4:
                            # 如果图表数量较少，使用标签页
                            tabs = st.tabs(tab_names)
                            for i, (chart_name, fig) in enumerate(charts.items()):
                                with tabs[i]:
                                    st.pyplot(fig)

                                    # 显示对应的数据表
                                    if market_share_data and chart_name in market_share_data:
                                        st.dataframe(
                                            market_share_data[chart_name].style.background_gradient(cmap='Greens'),
                                            use_container_width=True
                                        )
                        else:
                            # 如果图表数量较多，使用可折叠区域
                            for chart_name, fig in charts.items():
                                with st.expander(f"📊 {chart_name}", expanded=False):
                                    st.pyplot(fig)

                                    # 显示对应的数据表
                                    if market_share_data and chart_name in market_share_data:
                                        st.dataframe(
                                            market_share_data[chart_name].style.background_gradient(cmap='Greens'),
                                            use_container_width=True
                                        )
                    else:
                        st.warning("没有生成市场占有率图表")

            with col3:
                if st.button("💾 导出到Excel", type="primary", use_container_width=True, key="export_market_btn"):
                    excel_data = analyzer.export_market_share_analysis()

            # 显示数据概览
            st.markdown("---")
            st.subheader("数据概览")

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("总飞机数", len(analyzer.filtered_df))

            with col2:
                if 'Airline_Normalized' in analyzer.filtered_df.columns:
                    st.metric("航司数量", analyzer.filtered_df['Airline_Normalized'].nunique())

            with col3:
                if 'Manufacturer_Category' in analyzer.filtered_df.columns:
                    st.metric("制造商数量", analyzer.filtered_df['Manufacturer_Category'].nunique())

            with col4:
                if 'Master Series' in analyzer.filtered_df.columns:
                    st.metric("机型数量", analyzer.filtered_df['Master Series'].nunique())

            # 显示机型列表
            st.markdown("---")
            st.subheader("机型列表")
            model_list_df = analyzer.generate_model_list()
            if model_list_df is not None:
                st.dataframe(model_list_df, use_container_width=True)

    else:
        # 显示欢迎信息
        st.info("👈 请在侧边栏上传数据文件并点击'加载数据'开始分析")

        st.markdown("""
        ## 欢迎使用中国窄体机机龄分布与市场占有率分析工具

        本工具专为分析中国窄体机（含支线机）的机龄分布和市场占有率而设计。

        ### 主要功能:

        #### ✈️ 航司机龄分布分析
        - **航司x机型交叉表**: 查看各航司的机型组成
        - **机型x机龄分布**: 每个航司的详细机龄分布
        - **机龄分布图表**: 可视化显示各航司机龄分组
        - **Excel导出**: 完整的分析报告导出为Excel格式

        #### 📊 市场占有率分析
        - **制造商市场占有率**: 按飞机制造商分析市场份额
        - **机型市场占有率**: 按飞机型号分析市场份额
        - **按座位等级分类**: 按座位数分级分析市场占有率
        - **可视化图表**: 饼图显示市场分布
        - **Excel导出**: 详细的市场分析报告

        ### 数据要求:

        工具需要包含以下关键字段的Excel文件:

        | 字段 | 描述 | 必填 |
        |------|------|------|
        | Registration | 飞机注册号 | ✓ |
        | Operator | 运营航司 | ✓ |
        | Master Series | 飞机型号系列 | ✓ |
        | Manufacturer | 飞机制造商 | ✓ |
        | Age/Age字段 | 飞机机龄（年） | ✓ |
        | Status | 运营状态（In Service/Storage） | ✓ |
        | Operator State | 运营商所在省份 | ✓ |

        ### 使用方法:

        1. **准备数据**: 确保Excel文件包含所需字段
        2. **上传文件**: 在侧边栏上传数据文件
        3. **加载数据**: 点击"加载数据"处理和筛选数据
        4. **选择分析类型**: 在主页面选择航司分析或市场占有率分析
        5. **执行分析**: 使用分析按钮生成结果
        6. **导出结果**: 下载Excel报告进行进一步分析

        ### 技术支持:

        如有问题或需要数据模板，请联系开发者。

        **注意**: 处理大型数据集可能需要一些时间，请耐心等待。
        """)


if __name__ == "__main__":
    main()
