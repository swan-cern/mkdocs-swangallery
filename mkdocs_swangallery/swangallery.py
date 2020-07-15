from mkdocs.plugins import BasePlugin
from mkdocs.config import config_options
from mkdocs.structure.files import File
from bs4 import BeautifulSoup
from nbconvert import HTMLExporter
import re, os, copy, tempfile, shutil
import nbformat
import zipfile

isZipQueryParameter = '?clone_folder=True'
reString = '.ipynb(\?clone_folder=True)?$'
reMdString = '\[.*\]\((.*.ipynb(?:\?clone_folder=True)?)\)'

template_html = """<article>
    <a>
        <div class="background"></div>
        <h3></h3>
        <img alt="Click to open this example">
    </a>
</article>"""


class SwanGallery(BasePlugin):

    config_scheme = (
        ('notebook_dir', config_options.Type(str, default='notebooks')),
        ('open_in_swan_url', config_options.Type(str)),
        ('gallery_url', config_options.Type(str)),
    )

    def __init__(self):
        self.template = BeautifulSoup(template_html, "html.parser")
        self.tempFolder = tempfile.mkdtemp()

    def on_config(self, config):
        if not self.config['open_in_swan_url']:
            raise Exception('Configuration open_in_swan_url missing')
        config['open_in_swan_url'] = self.config['open_in_swan_url']
        if not self.config['gallery_url']:
            raise Exception('Configuration gallery_url missing')
        config['gallery_url'] = self.config['gallery_url']

        self.baseFolder = config['config_file_path'].replace('mkdocs.yml', '')
        self.NotebookDirName = self.config['notebook_dir']
        return config

    def on_files(self, files, config):

        notebooks = set()

        for page in files.documentation_pages():
            [notebooks.add(notebook) for notebook in self._get_notebooks_in_page(page)]

        for notebook in notebooks:
            isZip = isZipQueryParameter in notebook
            if isZip:
                notebook = notebook.replace(isZipQueryParameter, '')

            notebookFile = os.path.basename(notebook)
            originFolder = os.path.dirname(notebook)
            if isZip:
                pathSplit = originFolder.split('/')
                pathSplit.pop()
                originFolder = "/".join(pathSplit)
            destFolder = os.path.join(config['site_dir'], self.NotebookDirName, originFolder)

            # Convert notebook into a md file (stored in a temp folder) and add to files
            tempFile = self._generate_md_from_notebook(originFolder, notebookFile, isZip)
            tempName = os.path.join(self.NotebookDirName, originFolder, os.path.basename(tempFile))
            mkFile = File(tempName, self.tempFolder, config['site_dir'], False)
            files.append(mkFile)

            # Add the notebook snapshot to files to be copied over
            snapshotFile = notebookFile.replace('.ipynb', '.png')
            snapshotFolder = os.path.join(self.baseFolder, originFolder, 'nbSnapshots')
            nbSnapshot = File(snapshotFile, snapshotFolder, destFolder, False)
            files.append(nbSnapshot)

            # Also copy the original notebook file or the zip
            absOriginFolder = os.path.join(self.baseFolder, originFolder)
            if isZip:
                folderToZip = os.path.join(absOriginFolder, notebookFile.replace('.ipynb', ''))
                zipDestFile = tempFile.replace('.md', '.zip')
                self._zip_folder(folderToZip, zipDestFile)
                zipFile = File(tempName.replace('.md', '.zip'), self.tempFolder, config['site_dir'], False)
                files.append(zipFile)
            else:
                nbFile = File(notebookFile, absOriginFolder, destFolder, False)
                files.append(nbFile)

        return files

    def on_page_content(self, html, page, config, files):

        # This was a rendered notebook, do nothing...
        if "id='rendered_gallery_notebook'" in html:
            return html

        soup = BeautifulSoup(html, "html.parser")

        try:
            # Find all links that point to notebooks
            notebookLinks = soup.findAll(
                'a', attrs={'href': re.compile(reString)})

            # And replace them with the template
            for a in notebookLinks:
                # Convert the parent into div, but do it only once
                parent = a.find_parent('ul')
                if parent:
                    parent.name = 'div'
                    parent['class'] = 'gallery'

                href = a['href']
                text = a.getText()

                isZip = isZipQueryParameter in href
                if isZip:
                    href = href.replace(isZipQueryParameter, '')
                    # Remove the subfolder
                    pathSplit = href.split('/')
                    pathSplit.pop(-2)
                    href = "/".join(pathSplit)

                path = os.path.join('/%s' % self.NotebookDirName, *href.split('/')) # workaround for abs paths
                nbPath = path.replace('.ipynb', '.html')
                snapshotPath = path.replace('.ipynb', '.png')

                newElement = copy.copy(self.template)
                newElement.article.a['href'] = nbPath
                newElement.article.a.img['src'] = snapshotPath
                newElement.article.a.h3.string = text

                # Replace the li tag
                a.parent.replaceWith(newElement)

            return str(soup)

        except:
            pass

        return html

    def on_post_build(self, config):
        shutil.rmtree(self.tempFolder)

    def _get_notebooks_in_page(self, page):
        with open(page.abs_src_path) as file:
            raw_content = file.read()
            return re.findall(reMdString, raw_content)

    def _generate_md_from_notebook(self, originFolder, notebook, isZip = False):

        if isZip:
            originalFile = os.path.join(self.baseFolder, originFolder, notebook.replace('.ipynb', ''), notebook)
        else:
            originalFile = os.path.join(self.baseFolder, originFolder, notebook)
        destinationFolder = os.path.join(self.tempFolder, self.NotebookDirName, originFolder)
        destinationFile = os.path.join(destinationFolder, notebook.replace('.ipynb', '.md'))

        os.makedirs(destinationFolder, exist_ok=True)

        with open(originalFile) as nb:
            raw_content = nb.read()
            notebook_content = nbformat.reads(raw_content, as_version=4)

            html_exporter = HTMLExporter()
            html_exporter.template_file = 'basic'

            (body, resources) = html_exporter.from_notebook_node(notebook_content)

            full_content = "<style>\n"
            for style in resources['inlining']['css'][1:]:
                full_content += style
            full_content += "</style>\n"
            full_content += body

            # Add a special marker in this tag to be able to identify in the next stage
            full_content += "<div id='rendered_gallery_notebook'></div>"

            with open(destinationFile, 'w') as output:

                path = os.path.join('/%s' % self.NotebookDirName, *originFolder.split('/'), notebook) # workaround for abs paths
                if isZip:
                    path = path.replace('.ipynb', '.zip')

                output.write("---\n")
                output.write("template: notebook.html\n")
                output.write("notebook_name: %s\n" % notebook)
                output.write("notebook_url: %s\n" % path)
                output.write("---\n")
                output.write(full_content)

        return destinationFile

    def _zip_folder(self, folder, destination):
        zipf = zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED)
        for root, _, files in os.walk(folder):
            for file in files:
                relativeDir = os.path.relpath(root, folder)
                zipf.write(os.path.join(root, file), os.path.join(relativeDir, file))
        zipf.close()