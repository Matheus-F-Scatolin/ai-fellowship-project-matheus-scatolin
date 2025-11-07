// Aguarda o carregamento completo do DOM
document.addEventListener("DOMContentLoaded", () => {

    // Inicializa o highlight.js
    hljs.highlightAll();

    // Seleciona os elementos do DOM
    const form = document.getElementById("extract-form");
    const submitButton = document.getElementById("submit-button");
    const buttonText = document.getElementById("button-text");
    const spinner = document.getElementById("spinner");

    const resultSection = document.getElementById("result-section");
    const resultDataContainer = document.getElementById("result-data-container");
    const resultMetadataEl = document.getElementById("result-metadata");
    const errorEl = document.getElementById("error-message");
    
    // Elementos do formulário para validação em tempo real
    const schemaInput = document.getElementById("extraction_schema");

    // Adiciona validação em tempo real para o JSON schema
    schemaInput.addEventListener("input", () => {
        validateJsonSchema();
    });

    /**
     * Valida o JSON schema em tempo real e fornece feedback visual
     */
    function validateJsonSchema() {
        const value = schemaInput.value.trim();
        
        // Remove classes anteriores
        schemaInput.classList.remove("json-valid", "json-invalid");
        
        // Remove mensagens de erro anteriores
        const existingError = schemaInput.parentNode.querySelector(".json-error-message");
        if (existingError) {
            existingError.remove();
        }
        
        if (value === "") {
            // Campo vazio - estado neutro
            return;
        }
        
        try {
            const parsed = JSON.parse(value);
            
            // Verifica se é um objeto válido
            if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
                throw new Error("Use formato simples: {\"campo\": \"descrição\"}");
            }
            
            // Verifica se tem pelo menos um campo
            if (Object.keys(parsed).length === 0) {
                throw new Error("Deve conter pelo menos um campo");
            }
            
            // JSON válido
            schemaInput.classList.add("json-valid");
            
        } catch (error) {
            // JSON inválido
            schemaInput.classList.add("json-invalid");
            
            // Adiciona mensagem de erro
            const errorMessage = document.createElement("small");
            errorMessage.className = "json-error-message";
            errorMessage.style.color = "var(--pico-del-color)";
            errorMessage.style.marginTop = "0.25rem";
            errorMessage.style.display = "block";
            errorMessage.textContent = `JSON inválido: ${error.message}`;
            
            schemaInput.parentNode.appendChild(errorMessage);
        }
    }

    // Adiciona o listener de evento "submit" ao formulário
    form.addEventListener("submit", async (event) => {
        event.preventDefault(); // Impede o recarregamento da página

        // 1. Validações do lado cliente antes de enviar
        const validationError = validateForm();
        if (validationError) {
            displayError(validationError);
            return;
        }

        // 2. Mudar para o estado de "Carregando"
        setLoading(true);

        try {
            // 3. Montar o FormData
            const formData = new FormData(form);

            // 4. Fazer a chamada assíncrona para a API
            const response = await fetch("http://localhost:8000/extract", {
                method: "POST",
                body: formData,
            });

            // 5. Lidar com a resposta
            let result;
            try {
                result = await response.json();
            } catch (jsonError) {
                throw new Error("Erro ao processar resposta do servidor. Verifique se a API está funcionando corretamente.");
            }

            if (!response.ok) {
                // Se a API retornar um erro (ex: 400, 500)
                const errorMessage = formatApiError(result, response.status);
                throw new Error(errorMessage);
            }

            // 6. Exibir os resultados (Sucesso)
            displayResults(result);

        } catch (error) {
            // 7. Exibir erros (Falha)
            displayError(error.message);
        } finally {
            // 8. Resetar o estado de "Carregando"
            setLoading(false);
        }
    });

    /**
     * Valida o formulário do lado cliente antes de enviar
     * @returns {string|null} Mensagem de erro ou null se válido
     */
    function validateForm() {
        const labelInput = document.getElementById("label");
        const schemaInput = document.getElementById("extraction_schema");
        const fileInput = document.getElementById("file");

        // Valida se todos os campos estão preenchidos
        if (!labelInput.value.trim()) {
            return "❌ Por favor, preencha o campo 'Label (Tipo de Documento)'";
        }

        if (!schemaInput.value.trim()) {
            return "❌ Por favor, preencha o campo 'Schema de Extração (JSON)'";
        }

        if (!fileInput.files || fileInput.files.length === 0) {
            return "❌ Por favor, selecione um arquivo PDF";
        }

        // Valida se o arquivo é realmente um PDF
        const file = fileInput.files[0];
        if (!file.name.toLowerCase().endsWith('.pdf')) {
            return "❌ Por favor, selecione apenas arquivos PDF (.pdf)";
        }

        // Valida o tamanho do arquivo (máximo 10MB)
        const maxSize = 10 * 1024 * 1024; // 10MB
        if (file.size > maxSize) {
            return "❌ O arquivo é muito grande. Tamanho máximo permitido: 10MB";
        }

        // Valida se o JSON do schema é válido
        try {
            const parsedSchema = JSON.parse(schemaInput.value);
            
            // Verifica se é um objeto válido
            if (typeof parsedSchema !== 'object' || parsedSchema === null || Array.isArray(parsedSchema)) {
                return "❌ O Schema de Extração deve ser um objeto JSON simples.\n\nFormato correto: {\"campo\": \"descrição\"}\n\nNÃO use o formato completo com 'label', 'extraction_schema' e 'pdf_path'.";
            }

            // Verifica se tem pelo menos um campo
            if (Object.keys(parsedSchema).length === 0) {
                return "❌ O Schema de Extração deve conter pelo menos um campo para extrair";
            }

            // Verifica se os valores são strings
            for (const [key, value] of Object.entries(parsedSchema)) {
                if (typeof value !== 'string' || value.trim() === '') {
                    return `❌ O campo "${key}" no schema deve ter uma descrição válida (string não vazia)`;
                }
            }

        } catch (jsonError) {
            return `❌ JSON inválido no Schema de Extração: ${jsonError.message}\n\nDica: Use apenas o formato simples {"campo": "descrição"}\n\nExemplo correto:\n{\n  "nome": "Nome completo do profissional",\n  "inscricao": "Número de inscrição"\n}`;
        }

        return null; // Formulário válido
    }

    /**
     * Formata mensagens de erro da API de forma mais amigável
     * @param {object} result - Resposta de erro da API
     * @param {number} status - Status HTTP
     * @returns {string} Mensagem de erro formatada
     */
    function formatApiError(result, status) {
        const detail = result.detail || "Erro desconhecido";
        
        switch (status) {
            case 400:
                if (detail.includes("JSON")) {
                    return `❌ Erro no formato dos dados enviados: ${detail}\n\nVerifique se o Schema JSON está correto.`;
                }
                if (detail.includes("file")) {
                    return `❌ Erro no arquivo PDF: ${detail}\n\nVerifique se o arquivo não está corrompido.`;
                }
                return `❌ Dados inválidos: ${detail}`;
            
            case 413:
                return "❌ Arquivo muito grande. Tamanho máximo permitido: 10MB";
            
            case 415:
                return "❌ Tipo de arquivo não suportado. Apenas arquivos PDF são aceitos.";
            
            case 422:
                return `❌ Erro de validação: ${detail}\n\nVerifique se todos os campos estão preenchidos corretamente.`;
            
            case 500:
                return `❌ Erro interno do servidor: ${detail}\n\nTente novamente em alguns momentos.`;
            
            case 503:
                return "❌ Serviço temporariamente indisponível. Tente novamente em alguns momentos.";
            
            default:
                return `❌ Erro (${status}): ${detail}`;
        }
    }

    /**
     * Habilita/Desabilita o estado de carregamento da UI
     * @param {boolean} isLoading - True para mostrar o spinner, false para esconder
     */
    function setLoading(isLoading) {
        if (isLoading) {
            buttonText.textContent = "Extraindo...";
            spinner.hidden = false;
            submitButton.disabled = true;
            // Removido o aria-busy para evitar conflito com spinner do Pico.css

            // Limpa resultados anteriores
            resultSection.hidden = true;
            errorEl.hidden = true;
        } else {
            buttonText.textContent = "Extrair Dados";
            spinner.hidden = true;
            submitButton.disabled = false;
        }
    }

    /**
     * Exibe os dados e metadados na tela
     * @param {object} result - O objeto JSON retornado pela API
     */
    function displayResults(result) {
        // Separa dados e metadados
        const data = result.data;
        const metadata = result.metadata;
        
        // Exibe informações de performance
        displayPerformanceInfo(metadata);
        
        // Cria visualização bonita para os dados extraídos
        displayJsonData(data, resultDataContainer);
        
        // Formata metadados como JSON tradicional
        const metadataStr = JSON.stringify(metadata, null, 2);
        resultMetadataEl.textContent = metadataStr;
        hljs.highlightElement(resultMetadataEl);

        // Mostra a seção de resultados
        resultSection.hidden = false;
        errorEl.hidden = true;
    }

    /**
     * Exibe informações de performance da extração
     * @param {object} metadata - Metadados da resposta da API
     */
    function displayPerformanceInfo(metadata) {
        const performanceContainer = document.getElementById("performance-info");
        performanceContainer.innerHTML = '';

        // Extrai informações dos metadados
        const requestTime = metadata.request_time || 0;
        const fileName = metadata.file_name || 'arquivo';
        const fileSize = metadata.file_size || 0;
        const method = metadata._pipeline?.method || 'N/A';
        const steps = metadata._pipeline?.steps || [];

        // Cria métricas
        const metrics = [
            {
                label: '⏱️ Tempo de Extração',
                value: `${requestTime.toFixed(2)}s`,
                className: 'time'
            },
            {
                label: '🔧 Método Usado',
                value: formatPipelineMethod(method),
                className: 'method'
            },
            {
                label: `📏 Tamanho de ${fileName}`,
                value: formatFileSize(fileSize),
                className: 'size'
            }
        ];

        // Cria elementos HTML para cada métrica
        metrics.forEach(metric => {
            const metricDiv = document.createElement('div');
            metricDiv.className = 'performance-metric';

            const label = document.createElement('span');
            label.className = 'performance-metric-label';
            label.textContent = metric.label;

            const value = document.createElement('span');
            value.className = `performance-metric-value ${metric.className}`;
            value.textContent = metric.value;

            metricDiv.appendChild(label);
            metricDiv.appendChild(value);

            // Adiciona subtítulo se houver
            if (metric.subtitle) {
                const subtitle = document.createElement('div');
                subtitle.className = 'pipeline-steps';
                subtitle.textContent = metric.subtitle;
                metricDiv.appendChild(subtitle);
            }

            performanceContainer.appendChild(metricDiv);
        });
    }

    /**
     * Formata o método da pipeline de forma mais legível
     * @param {string} method - Método da pipeline
     * @returns {string} Método formatado
     */
    function formatPipelineMethod(method) {
        if (!method || method === 'N/A') return 'N/A';
        
        // Mapeia métodos para nomes mais amigáveis
        const methodMap = {
            'llm-full': '🤖 LLM Completo',
            'cache-l1': '💾 Cache L1',
            'cache-l2': '💾 Cache L2', 
            'cache-l3': '🔄 Cache L3',
            'template': '🎭 Template',
            'llm-fallback': '🆘 LLM Fallback'
        };

        // Se contém '->', é uma sequência de métodos
        if (method.includes('->')) {
            const parts = method.split('->');
            return parts.map(part => methodMap[part.trim()] || part.trim()).join(' → ');
        }

        return methodMap[method] || method;
    }

    /**
     * Formata o tamanho do arquivo de forma legível
     * @param {number} bytes - Tamanho em bytes
     * @returns {string} Tamanho formatado
     */
    function formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
    }

    /**
     * Cria uma visualização bonita e organizada para os dados JSON
     * @param {object} data - Os dados extraídos
     * @param {Element} container - Container onde exibir os dados
     */
    function displayJsonData(data, container) {
        // Limpa o container
        container.innerHTML = '';
        
        // Cria o viewer principal
        const jsonViewer = document.createElement('div');
        jsonViewer.className = 'json-viewer';
        
        if (!data || Object.keys(data).length === 0) {
            jsonViewer.innerHTML = '<p style="color: var(--pico-muted-color); text-align: center; font-style: italic;">Nenhum dado foi extraído</p>';
            container.appendChild(jsonViewer);
            return;
        }
        
        // Cria campos individuais para cada propriedade
        Object.entries(data).forEach(([key, value]) => {
            const fieldDiv = document.createElement('div');
            fieldDiv.className = 'json-field';
            
            const keySpan = document.createElement('span');
            keySpan.className = 'json-field-key';
            keySpan.textContent = key;
            
            const valueDiv = document.createElement('div');
            valueDiv.className = 'json-field-value';
            
            // Formata o valor baseado no tipo
            if (value === null || value === undefined || value === '') {
                valueDiv.textContent = '(não encontrado)';
                valueDiv.classList.add('null-value');
            } else if (typeof value === 'object') {
                valueDiv.textContent = JSON.stringify(value, null, 2);
            } else {
                valueDiv.textContent = String(value);
            }
            
            fieldDiv.appendChild(keySpan);
            fieldDiv.appendChild(valueDiv);
            jsonViewer.appendChild(fieldDiv);
        });
        
        container.appendChild(jsonViewer);
    }

    /**
     * Exibe uma mensagem de erro na tela de forma organizada
     * @param {string} message - A mensagem de erro
     */
    function displayError(message) {
        // Limpa conteúdo anterior
        errorEl.innerHTML = '';
        
        // Cria container para o erro
        const errorContainer = document.createElement('div');
        
        // Se a mensagem contém quebras de linha, trata como múltiplas linhas
        if (message.includes('\n')) {
            const lines = message.split('\n');
            lines.forEach((line, index) => {
                if (line.trim()) {
                    const lineElement = document.createElement('p');
                    lineElement.textContent = line;
                    lineElement.style.margin = index === 0 ? '0 0 0.5rem 0' : '0.25rem 0';
                    
                    // Destaca a primeira linha (título do erro)
                    if (index === 0) {
                        lineElement.style.fontWeight = 'bold';
                        lineElement.style.fontSize = '1.1rem';
                    }
                    
                    errorContainer.appendChild(lineElement);
                }
            });
        } else {
            // Mensagem simples
            const errorText = document.createElement('p');
            errorText.textContent = message;
            errorText.style.margin = '0';
            errorText.style.fontWeight = 'bold';
            errorContainer.appendChild(errorText);
        }
        
        errorEl.appendChild(errorContainer);
        errorEl.hidden = false;
        resultSection.hidden = true;
        
        // Scroll para o erro para garantir que seja visível
        errorEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
});