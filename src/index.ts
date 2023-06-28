import { IDisposable, DisposableDelegate } from '@lumino/disposable';
import {
  JupyterFrontEnd,
  JupyterFrontEndPlugin,
} from '@jupyterlab/application';
import { ToolbarButton } from '@jupyterlab/apputils';
import { DocumentRegistry } from '@jupyterlab/docregistry';
import {
  NotebookPanel,
  INotebookModel,
} from '@jupyterlab/notebook';
import { 
  KernelMessage,
  Kernel,
} from '@jupyterlab/services';
import {IMimeBundle} from "@jupyterlab/nbformat";


const plugin: JupyterFrontEndPlugin<void> = {
  activate,
  id: 'toolbar-button',
  autoStart: true,
};

export class ButtonExtension
  implements DocumentRegistry.IWidgetExtension<NotebookPanel, INotebookModel>
{
  createNew(
    panel: NotebookPanel,
    context: DocumentRegistry.IContext<INotebookModel>
  ): IDisposable {
    async function runCondaExport(): Promise<void> {
      const kernel = panel.sessionContext.session?.kernel;
      if (!kernel) {
        console.error('No kernel found.');
        return;
      }

      const envPrefixCode = 'import sys; sys.prefix';
      const envPrefixFuture = kernel.requestExecute({ code: envPrefixCode });

      // Listen for IOPub messages
      const iopubHandler = (
        sender: Kernel.IKernelConnection,
        msg: KernelMessage.IIOPubMessage
      ) => {
        if (msg.header.msg_type === 'execute_result') {
          const content = msg.content as KernelMessage.IExecuteResultMsg['content'];
          const data = content.data as IMimeBundle;
          let envPrefix = data['text/plain'] as string;
          envPrefix = envPrefix.replace(/^'/, '').replace(/'$/, '');
          
          const buttonCommand = `!source $EXTENSIONS_DIR/toolbar-button/button_script.sh ${envPrefix}`;
            
          kernel.requestExecute({ code: buttonCommand, stop_on_error: true });

        }
      };

      // Subscribe to IOPub messages
      kernel.iopubMessage.connect(iopubHandler);

      // Wait for the execution to complete
      await envPrefixFuture.done;

      // Unsubscribe from IOPub messages
      kernel.iopubMessage.disconnect(iopubHandler);

    }    

    const button = new ToolbarButton({
      className: 'export-button',
      label: 'Export Environment',
      onClick: runCondaExport,
      tooltip: 'Export Environment',
    });

    panel.toolbar.insertItem(10, 'exportButton', button);
    return new DisposableDelegate(() => {
      button.dispose();
    });
  }
}

function activate(app: JupyterFrontEnd): void {
  app.docRegistry.addWidgetExtension('Notebook', new ButtonExtension());
}

export default plugin;
