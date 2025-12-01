#!/usr/bin/env python3
"""
ANALISADOR DE RESULTADOS DOS TESTES
Processa logs e gera relatórios de performance
"""

import json
import os
import re
import glob
from datetime import datetime
import matplotlib.pyplot as plt
import pandas as pd
from collections import defaultdict

class TestResultAnalyzer:
    def __init__(self):
        self.log_dir = "test_logs"
        self.report_dir = "test_reports" 
        
        # Criar diretórios se não existirem
        os.makedirs(self.log_dir, exist_ok=True)
        os.makedirs(self.report_dir, exist_ok=True)
    
    def find_log_files(self):
        """Encontra todos os arquivos de log de teste"""
        patterns = [
            "test_*.log",
            "stress_*.log", 
            "component_*.log",
            "monitor_*.log"
        ]
        
        log_files = []
        for pattern in patterns:
            log_files.extend(glob.glob(os.path.join(self.log_dir, pattern)))
        
        return sorted(log_files)
    
    def parse_stress_test_log(self, log_file):
        """Parse dos logs do teste de estresse"""
        results = {
            "timestamp": None,
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "avg_response_time": 0,
            "max_response_time": 0,
            "min_response_time": float('inf'),
            "error_rate": 0,
            "throughput": 0
        }
        
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extrair estatísticas principais
            if "Requests totais:" in content:
                match = re.search(r'Requests totais:\s*(\d+)', content)
                if match:
                    results["total_requests"] = int(match.group(1))
            
            if "Sucesso:" in content:
                match = re.search(r'Sucesso:\s*(\d+)', content)
                if match:
                    results["successful_requests"] = int(match.group(1))
            
            if "Falhas:" in content:
                match = re.search(r'Falhas:\s*(\d+)', content)
                if match:
                    results["failed_requests"] = int(match.group(1))
            
            if "Taxa de erro:" in content:
                match = re.search(r'Taxa de erro:\s*([\d.]+)%', content)
                if match:
                    results["error_rate"] = float(match.group(1))
            
            if "Tempo médio:" in content:
                match = re.search(r'Tempo médio:\s*([\d.]+)s', content)
                if match:
                    results["avg_response_time"] = float(match.group(1))
            
            if "Throughput:" in content:
                match = re.search(r'Throughput:\s*([\d.]+)\s*req/s', content)
                if match:
                    results["throughput"] = float(match.group(1))
            
            # Timestamp do arquivo
            results["timestamp"] = datetime.fromtimestamp(os.path.getmtime(log_file))
            
        except Exception as e:
            print(f"Erro ao processar {log_file}: {e}")
        
        return results
    
    def parse_monitor_log(self, log_file):
        """Parse dos logs do monitor de sistema"""
        metrics = {
            "cpu_usage": [],
            "ram_usage": [],
            "ffmpeg_processes": [],
            "timestamps": []
        }
        
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if "CPU:" in line and "RAM:" in line:
                        # Extrair métricas da linha
                        cpu_match = re.search(r'CPU:\s*([\d.]+)%', line)
                        ram_match = re.search(r'RAM:\s*([\d.]+)%', line)
                        ffmpeg_match = re.search(r'FFmpeg:\s*(\d+)\s*processos', line)
                        
                        if cpu_match and ram_match:
                            metrics["cpu_usage"].append(float(cpu_match.group(1)))
                            metrics["ram_usage"].append(float(ram_match.group(1)))
                            
                            if ffmpeg_match:
                                metrics["ffmpeg_processes"].append(int(ffmpeg_match.group(1)))
                            else:
                                metrics["ffmpeg_processes"].append(0)
                            
                            # Timestamp aproximado (pode não ser exato)
                            metrics["timestamps"].append(datetime.now())
        
        except Exception as e:
            print(f"Erro ao processar monitor log {log_file}: {e}")
        
        return metrics
    
    def generate_summary_report(self, test_results):
        """Gera relatório resumo dos testes"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = os.path.join(self.report_dir, f"summary_report_{timestamp}.md")
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("# 📊 RELATÓRIO DE TESTES DE PERFORMANCE\n\n")
            f.write(f"**Gerado em:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n")
            
            if not test_results:
                f.write("❌ Nenhum resultado de teste encontrado.\n")
                return report_file
            
            f.write("## 📈 RESUMO EXECUTIVO\n\n")
            
            # Calcular médias
            total_tests = len(test_results)
            avg_error_rate = sum(r["error_rate"] for r in test_results) / total_tests
            avg_response_time = sum(r["avg_response_time"] for r in test_results) / total_tests
            avg_throughput = sum(r["throughput"] for r in test_results) / total_tests
            
            # Status geral
            status = "🟢 BOM"
            if avg_error_rate > 10 or avg_response_time > 3:
                status = "🔴 CRÍTICO"
            elif avg_error_rate > 5 or avg_response_time > 2:
                status = "🟡 ATENÇÃO"
            
            f.write(f"**Status Geral:** {status}\n")
            f.write(f"**Total de Testes:** {total_tests}\n")
            f.write(f"**Taxa de Erro Média:** {avg_error_rate:.2f}%\n")
            f.write(f"**Tempo de Resposta Médio:** {avg_response_time:.3f}s\n")
            f.write(f"**Throughput Médio:** {avg_throughput:.1f} req/s\n\n")
            
            f.write("## 📋 DETALHES DOS TESTES\n\n")
            
            for i, result in enumerate(test_results, 1):
                f.write(f"### Teste #{i}\n")
                f.write(f"**Timestamp:** {result['timestamp']}\n")
                f.write(f"**Requests Totais:** {result['total_requests']}\n")
                f.write(f"**Taxa de Sucesso:** {result['successful_requests']}/{result['total_requests']} ({(result['successful_requests']/max(result['total_requests'],1)*100):.1f}%)\n")
                f.write(f"**Taxa de Erro:** {result['error_rate']:.2f}%\n")
                f.write(f"**Tempo de Resposta:** {result['avg_response_time']:.3f}s\n")
                f.write(f"**Throughput:** {result['throughput']:.1f} req/s\n\n")
            
            f.write("## 🎯 RECOMENDAÇÕES\n\n")
            
            if avg_error_rate > 10:
                f.write("🔴 **CRÍTICO:** Taxa de erro muito alta (>10%)\n")
                f.write("   - Verificar logs de erro do Flask\n")
                f.write("   - Analisar capacidade do banco de dados\n")
                f.write("   - Considerar otimizações de código\n\n")
            
            if avg_response_time > 3:
                f.write("🔴 **CRÍTICO:** Tempo de resposta muito lento (>3s)\n")
                f.write("   - Otimizar queries do banco\n")
                f.write("   - Verificar gargalos de I/O\n")
                f.write("   - Considerar cache\n\n")
            
            if avg_throughput < 10:
                f.write("🟡 **ATENÇÃO:** Throughput baixo (<10 req/s)\n")
                f.write("   - Verificar configuração do Flask\n")
                f.write("   - Analisar recursos de CPU/RAM\n")
                f.write("   - Considerar scaling horizontal\n\n")
            
            if avg_error_rate < 5 and avg_response_time < 2:
                f.write("🟢 **EXCELENTE:** Sistema está performando bem!\n")
                f.write("   - Manter monitoramento regular\n")
                f.write("   - Considerar testes com carga maior\n\n")
        
        return report_file
    
    def generate_charts(self, monitor_metrics):
        """Gera gráficos de monitoramento"""
        if not monitor_metrics["cpu_usage"]:
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        chart_file = os.path.join(self.report_dir, f"performance_chart_{timestamp}.png")
        
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
        
        time_range = range(len(monitor_metrics["cpu_usage"]))
        
        # CPU Usage
        ax1.plot(time_range, monitor_metrics["cpu_usage"], 'b-', linewidth=2)
        ax1.set_title('📊 Uso de CPU (%)')
        ax1.set_ylabel('CPU %')
        ax1.grid(True)
        ax1.axhline(y=70, color='orange', linestyle='--', alpha=0.7, label='Atenção (70%)')
        ax1.axhline(y=90, color='red', linestyle='--', alpha=0.7, label='Crítico (90%)')
        ax1.legend()
        
        # RAM Usage  
        ax2.plot(time_range, monitor_metrics["ram_usage"], 'g-', linewidth=2)
        ax2.set_title('💾 Uso de RAM (%)')
        ax2.set_ylabel('RAM %')
        ax2.grid(True)
        ax2.axhline(y=80, color='orange', linestyle='--', alpha=0.7, label='Atenção (80%)')
        ax2.axhline(y=90, color='red', linestyle='--', alpha=0.7, label='Crítico (90%)')
        ax2.legend()
        
        # FFmpeg Processes
        ax3.plot(time_range, monitor_metrics["ffmpeg_processes"], 'r-', linewidth=2, marker='o')
        ax3.set_title('🎬 Processos FFmpeg')
        ax3.set_ylabel('Quantidade')
        ax3.grid(True)
        
        # CPU vs RAM
        ax4.scatter(monitor_metrics["cpu_usage"], monitor_metrics["ram_usage"], alpha=0.6)
        ax4.set_title('🔄 CPU vs RAM')
        ax4.set_xlabel('CPU %')
        ax4.set_ylabel('RAM %')
        ax4.grid(True)
        
        plt.tight_layout()
        plt.savefig(chart_file, dpi=150, bbox_inches='tight')
        plt.close()
        
        return chart_file
    
    def analyze_all(self):
        """Análise completa de todos os logs"""
        print("🔍 Procurando arquivos de log...")
        log_files = self.find_log_files()
        
        if not log_files:
            print("❌ Nenhum arquivo de log encontrado.")
            print(f"💡 Logs devem estar em: {self.log_dir}")
            return
        
        print(f"📁 Encontrados {len(log_files)} arquivos de log")
        
        # Processar logs de teste de estresse
        test_results = []
        monitor_metrics = {"cpu_usage": [], "ram_usage": [], "ffmpeg_processes": [], "timestamps": []}
        
        for log_file in log_files:
            print(f"📖 Processando: {os.path.basename(log_file)}")
            
            if "stress" in log_file or "component" in log_file:
                result = self.parse_stress_test_log(log_file)
                if result["total_requests"] > 0:
                    test_results.append(result)
            
            elif "monitor" in log_file:
                metrics = self.parse_monitor_log(log_file)
                if metrics["cpu_usage"]:
                    # Combinar métricas (simplificado)
                    monitor_metrics["cpu_usage"].extend(metrics["cpu_usage"])
                    monitor_metrics["ram_usage"].extend(metrics["ram_usage"])
                    monitor_metrics["ffmpeg_processes"].extend(metrics["ffmpeg_processes"])
        
        if test_results:
            print("📊 Gerando relatório de resumo...")
            report_file = self.generate_summary_report(test_results)
            print(f"✅ Relatório gerado: {report_file}")
        
        if monitor_metrics["cpu_usage"]:
            print("📈 Gerando gráficos...")
            chart_file = self.generate_charts(monitor_metrics)
            if chart_file:
                print(f"✅ Gráficos gerados: {chart_file}")
        
        print("\n🎉 Análise concluída!")
        print(f"📂 Relatórios salvos em: {self.report_dir}")

def main():
    analyzer = TestResultAnalyzer()
    analyzer.analyze_all()

if __name__ == "__main__":
    main()