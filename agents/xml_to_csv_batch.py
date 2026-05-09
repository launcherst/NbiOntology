import xml.etree.ElementTree as ET
import csv
import os
import glob
import fnmatch
import zipfile
import gzip
import shutil
import tempfile

def extract_and_convert_archive(archive_path, temp_dir):
    """
    解压ZIP或GZ文件，返回解压后的XML文件路径列表
    
    参数:
        archive_path: 压缩文件路径
        temp_dir: 临时目录路径
    
    返回:
        list: 解压后的XML文件路径列表
    """
    xml_files = []
    file_ext = os.path.splitext(archive_path)[1].lower()
    
    try:
        if file_ext == '.zip':
            # 解压ZIP文件
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                for member in zip_ref.namelist():
                    # 跳过目录和隐藏文件
                    if member.endswith('/') or os.path.basename(member).startswith('.'):
                        continue
                    # 只解压XML文件
                    if member.lower().endswith('.xml'):
                        zip_ref.extract(member, temp_dir)
                        extracted_path = os.path.join(temp_dir, member)
                        xml_files.append(extracted_path)
                        print(f"  解压: {member}")
                        
        elif file_ext == '.gz':
            # 解压GZ文件
            base_name = os.path.basename(archive_path)
            # 移除.gz后缀作为输出文件名
            if base_name.lower().endswith('.xml.gz'):
                output_name = base_name[:-3]  # 移除.gz
            elif base_name.lower().endswith('.gz'):
                output_name = base_name[:-3]
            else:
                output_name = base_name + '.xml'
            
            output_path = os.path.join(temp_dir, output_name)
            with gzip.open(archive_path, 'rb') as f_in:
                with open(output_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # 检查解压后的文件是否是XML
            if output_path.lower().endswith('.xml'):
                xml_files.append(output_path)
                print(f"  解压: {base_name} -> {output_name}")
                
    except Exception as e:
        print(f"  解压失败: {os.path.basename(archive_path)} - {str(e)}")
    
    return xml_files


def is_archive_file(file_path):
    """
    检查文件是否为支持的压缩格式
    """
    ext = os.path.splitext(file_path)[1].lower()
    return ext in ['.zip', '.gz']


def convert_otn_xml_to_csv(xml_file_path, csv_file_path=None, is_temp_file=False):
    """
    将单个OTN NEL XML文件转换为CSV格式
    
    参数:
        xml_file_path: XML文件路径
        csv_file_path: 输出CSV文件路径，None则自动生成
        is_temp_file: 是否为临时文件，临时文件会在转换后删除
    """
    try:
        # 解析XML文件
        tree = ET.parse(xml_file_path)
        root = tree.getroot()
        
        # 提取字段名称
        field_names = []
        field_name_elem = root.find('.//FieldName')
        if field_name_elem is not None:
            # 按i属性排序获取字段名
            fields = {}
            for n_elem in field_name_elem.findall('N'):
                i_value = n_elem.get('i')
                field_name = n_elem.text
                fields[int(i_value)] = field_name
            
            # 按序号排序字段
            field_names = [fields[i] for i in sorted(fields.keys())]
        
        # 添加rmUID作为第一列
        headers = ['rmUID'] + field_names
        
        # 提取数据
        data_rows = []
        field_value_elem = root.find('.//FieldValue')
        if field_value_elem is not None:
            for object_elem in field_value_elem.findall('Object'):
                rmUID = object_elem.get('rmUID', '')
                
                # 提取值并按i属性排序
                values = {}
                for v_elem in object_elem.findall('V'):
                    i_value = v_elem.get('i')
                    value_text = v_elem.text if v_elem.text else ''
                    values[int(i_value)] = value_text
                
                # 按序号排序值
                sorted_values = [values[i] for i in sorted(values.keys())]
                
                # 创建完整行数据
                row_data = [rmUID] + sorted_values
                data_rows.append(row_data)
        
        # 如果未指定CSV文件路径，则自动生成
        if csv_file_path is None:
            base_name = os.path.splitext(xml_file_path)[0]
            csv_file_path = base_name + '.csv'
        
        # 写入CSV文件
        with open(csv_file_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.writer(csvfile)
            
            # 写入表头
            writer.writerow(headers)
            
            # 写入数据
            for row in data_rows:
                writer.writerow(row)
        
        print(f"✓ 转换成功: {os.path.basename(xml_file_path)} → {os.path.basename(csv_file_path)}")
        print(f"  记录数量: {len(data_rows)}, 字段数量: {len(headers)}")
        
        # 如果是临时文件，转换后删除
        if is_temp_file and os.path.exists(xml_file_path):
            try:
                os.remove(xml_file_path)
            except:
                pass
        
        return True
        
    except Exception as e:
        print(f"✗ 转换失败 {os.path.basename(xml_file_path)}: {str(e)}")
        # 如果是临时文件，即使转换失败也尝试删除
        if is_temp_file and os.path.exists(xml_file_path):
            try:
                os.remove(xml_file_path)
            except:
                pass
        return False

def process_file(file_path, temp_dir=None, output_dir=None):
    """
    处理单个文件（XML或压缩文件）
    
    参数:
        file_path: 文件路径
        temp_dir: 临时目录（用于解压）
        output_dir: CSV输出目录，None则使用原文件所在目录
    
    返回:
        int: 成功转换的文件数量
    """
    success_count = 0
    
    if is_archive_file(file_path):
        # 处理压缩文件
        print(f"\n检测到压缩文件: {os.path.basename(file_path)}")
        
        # 创建临时目录
        if temp_dir is None:
            temp_dir = tempfile.mkdtemp()
            cleanup_temp = True
        else:
            cleanup_temp = False
        
        try:
            # 解压文件
            extracted_files = extract_and_convert_archive(file_path, temp_dir)
            
            if not extracted_files:
                print(f"  未找到XML文件")
                return 0
            
            # 确定输出目录
            if output_dir is None:
                output_dir = os.path.dirname(file_path)
            
            # 转换解压后的XML文件
            for xml_file in extracted_files:
                # 生成CSV文件名（基于原压缩文件名+XML文件名）
                archive_name = os.path.splitext(os.path.basename(file_path))[0]
                xml_name = os.path.splitext(os.path.basename(xml_file))[0]
                
                # 如果是ZIP中的文件，避免文件名冲突
                if file_path.lower().endswith('.zip'):
                    csv_name = f"{archive_name}_{xml_name}.csv"
                else:
                    csv_name = f"{xml_name}.csv"
                
                csv_path = os.path.join(output_dir, csv_name)
                
                if convert_otn_xml_to_csv(xml_file, csv_path, is_temp_file=True):
                    success_count += 1
                    
        finally:
            # 清理临时目录
            if cleanup_temp and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except:
                    pass
                    
    else:
        # 直接处理XML文件
        if output_dir:
            csv_name = os.path.splitext(os.path.basename(file_path))[0] + '.csv'
            csv_path = os.path.join(output_dir, csv_name)
        else:
            csv_path = None
            
        if convert_otn_xml_to_csv(file_path, csv_path, is_temp_file=False):
            success_count += 1
    
    return success_count


def batch_convert_xml_in_directory(directory_path, file_pattern="*.xml", recursive=False):
    """
    批量转换目录中的XML文件为CSV文件（支持ZIP和GZ压缩文件）
    
    参数:
        directory_path: 要扫描的目录路径
        file_pattern: 文件匹配模式，默认为"*.xml"
        recursive: 是否递归扫描子目录，默认为False
    """
    if not os.path.exists(directory_path):
        print(f"错误: 目录不存在 - {directory_path}")
        return
    
    print(f"开始扫描目录: {directory_path}")
    
    # 创建临时目录用于解压
    temp_dir = tempfile.mkdtemp()
    
    try:
        # 搜索XML文件
        if recursive:
            xml_files = []
            for root_dir, _, files in os.walk(directory_path):
                for file in files:
                    if fnmatch.fnmatch(file, file_pattern):
                        xml_files.append(os.path.join(root_dir, file))
        else:
            search_pattern = os.path.join(directory_path, file_pattern)
            xml_files = glob.glob(search_pattern)
        
        # 搜索压缩文件
        archive_patterns = ['*.zip', '*.gz']
        archive_files = []
        
        if recursive:
            for root_dir, _, files in os.walk(directory_path):
                for file in files:
                    if any(fnmatch.fnmatch(file, pattern) for pattern in archive_patterns):
                        archive_files.append(os.path.join(root_dir, file))
        else:
            for pattern in archive_patterns:
                search_pattern = os.path.join(directory_path, pattern)
                archive_files.extend(glob.glob(search_pattern))
        
        # 合并文件列表
        all_files = xml_files + archive_files
        
        if not all_files:
            print(f"在目录 {directory_path} 中未找到XML或压缩文件")
            return
        
        print(f"找到 {len(xml_files)} 个XML文件, {len(archive_files)} 个压缩文件")
        
        # 处理所有文件
        total_success = 0
        for file_path in all_files:
            total_success += process_file(file_path, temp_dir)
        
        print(f"\n批量转换完成!")
        print(f"成功转换: {total_success}/{len(all_files)} 个文件")
        
    finally:
        # 清理临时目录
        if os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except:
                pass

def main():
    """
    主函数 - 提供用户交互界面
    """
    print("OTN NEL XML/ZIP/GZ 批量转 CSV 转换工具")
    print("=" * 50)
    
    while True:
        print("\n请选择操作:")
        print("1. 转换单个文件（支持 .xml / .zip / .gz）")
        print("2. 批量转换当前目录中的文件")
        print("3. 批量转换目录及子目录中的文件")
        print("4. 退出")
        
        choice = input("请输入选择 (1-4): ").strip()
        
        if choice == '1':
            xml_file = input("请输入XML文件路径: ").strip()
            if not os.path.exists(xml_file):
                print("文件不存在，请检查路径")
                continue
            
            # 检查是否为压缩文件
            if is_archive_file(xml_file):
                process_file(xml_file)
            else:
                # 可选：自定义输出文件名
                custom_output = input("请输入输出CSV文件路径 (直接回车使用默认名称): ").strip()
                if not custom_output:
                    custom_output = None
                
                convert_otn_xml_to_csv(xml_file, custom_output)
            
        elif choice == '2':
            directory = input("请输入包含XML文件的目录路径: ").strip()
            batch_convert_xml_in_directory(directory, recursive=False)
            
        elif choice == '3':
            directory = input("请输入包含XML文件的目录路径: ").strip()
            batch_convert_xml_in_directory(directory, recursive=True)
            
        elif choice == '4':
            print("谢谢使用！")
            break
        else:
            print("无效选择，请重新输入")

# 直接批量转换指定目录的函数
def quick_batch_convert(directory_path):
    """
    快速批量转换指定目录中的所有XML文件
    """
    print(f"快速批量转换: {directory_path}")
    batch_convert_xml_in_directory(directory_path)

if __name__ == "__main__":
    # 运行交互式主程序
    main()