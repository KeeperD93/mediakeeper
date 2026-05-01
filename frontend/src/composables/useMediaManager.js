/**
 * useMediaManager — facade exposing state/methods from domain submodules.
 * State lives at module level in mediaManagerState.js so all callers share
 * the same refs (see related composable pattern used by useStats/useStatsUI).
 */

import { useI18n } from 'vue-i18n'
import {
  CATS, catsLoaded, activeCat, subPath, files, filtered, checked, loading,
  filterQuery, sortMode, expandedMode, tags,
  searchType, tmdbResults, selectedTmdb, currentSeason, seasons, showSeasonPanel,
  tooltip, newNames, renaming, dragSrc, progress,
  modalConfirm, modalFolders, modalMoveShow, modalMoveSrc,
  moveCat, movePath, moveFolders, moveSearchQ, moveSelectedPath, moveLoading, moveManualPath,
  modalRenameFolderShow, renameFolderCurrent, renameFolderValue,
  folderSeriesName, folderAudioTags, folderBatchAudioTags, folderSeasonTags, folderPreview, folderExistingDirs,
  dragFileIdx, dragIsGrouped, dragOverCat,
  renameHistory, moveHistory, showMoveHistoryModal,
  namingIssues, analysisActive,
  renameProfiles, anomalyRules, showAnomalyConfigModal,
  multiCatMode, extractionRunning,
  fileRenameStatus, thumbnailCache,
  moveConflicts, showMoveConflictModal,
  fileMetaModal, renameErrors, showRenameErrorsModal,
  customRules, releaseTags, releaseTagsDefaults, releaseTagsLoaded, showAdvancedModal, advancedTab,
  crossCatDuplicates, checkingDuplicates,
  setT,
} from './mediaManagerState'
import { sanitize, cleanName, getGenreCategory, computeQualityScore, getQualityColor, computeDiff, detectSeasonNum, isFileNew } from './mediaManagerHelpers'
import {
  loadCategories, addCategory, removeCategory,
  breadcrumbs, fileCount, checkedFiles, checkedDirs, hasChecked, newFilesCount,
  setCat, enterDir, navRoot, navTo, navBack, loadFiles, applyRenameInPlace,
  applyFilter, sortLeft, toggleCheck, toggleAll, toggleMultiCat,
  deleteFile, deleteSelected, getFileCat, refreshEmby,
} from './mediaManagerNavigation'
import {
  fileDragStart, fileDragEnd, dropOnCat, dropOnFolder,
  execMoveWithOverwrite, cancelMoveConflict,
} from './mediaManagerMove'
import {
  canGenerate, canRename,
  setType, doSearch, pickTMDB, loadSeasons,
  showTooltipTmdb, moveTooltip, hideTooltip, autoSearch,
  fuzzyTmdbSearch,
} from './mediaManagerTmdb'
import {
  expandCheckedFolders, cancelExtraction, extractFromSubfolders,
  doMatch, dropOnTmdb,
} from './mediaManagerMatch'
import {
  startRename, execRename, clearRenameErrors,
  undoRename, clearRenameHistory,
  dStart, dDrop, removeRight, clearRight,
} from './mediaManagerRename'
import {
  moveFoldersFiltered, moveBreadcrumbs, canMoveMulti,
  suggestedMoveFolder, suggestedParentName,
  moveTargetPreview, recentMoveDestinations, moveSourcesCount,
  jumpToAbsolutePath, applyManualPath,
  openMoveModal, openMoveModalMulti, closeMoveModal, execMove,
  moveChangeCat, moveEnterFolder, moveNavTo, moveNavRoot, movePickFolder, movePickCurrent,
  createMoveFolder,
  undoMove, clearMoveHistory,
  openRenameFolderModal, execRenameFolder,
} from './mediaManagerMoveModal'
import {
  canFolders,
  openFolderModal, toggleAudioTag, toggleBatchAudioTag, autoDetectFolders, updateFolderPreview,
  execFolderOrganize, execRenameAllFolders,
} from './mediaManagerFolderModal'
import { openFileMeta, closeFileMeta, loadThumbnail } from './mediaManagerMeta'
import {
  saveAnomalyRules, issuesCount,
  analyzeNames, clearAnalysis,
  getAllProfiles, saveProfile, deleteProfile, applyProfile,
  addCustomRule, deleteCustomRule, applyCustomRules,
  loadReleaseTags, saveReleaseTags, resetReleaseTags,
  checkCrossCatDuplicates,
  exportRenameCsv, importRenameCsv,
} from './mediaManagerRules'

export { CATS }

export function useMediaManager() {
  const { t } = useI18n()
  setT(t)
  return {
    CATS, catsLoaded, activeCat, subPath, files, filtered, checked, loading,
    loadCategories, addCategory, removeCategory,
    filterQuery, sortMode, expandedMode, tags,
    searchType, tmdbResults, selectedTmdb, currentSeason, seasons, showSeasonPanel,
    tooltip, newNames, renaming, dragSrc, progress,
    modalConfirm, modalFolders, modalMoveShow, modalMoveSrc,
    moveCat, movePath, moveFolders, moveFoldersFiltered, moveSearchQ,
    moveSelectedPath, moveLoading, moveBreadcrumbs, moveManualPath,
    moveTargetPreview, recentMoveDestinations, moveSourcesCount,
    jumpToAbsolutePath, applyManualPath,
    modalRenameFolderShow, renameFolderCurrent, renameFolderValue,
    folderSeriesName, folderAudioTags, folderBatchAudioTags, folderSeasonTags, folderPreview, folderExistingDirs,
    dragFileIdx, dragIsGrouped, dragOverCat,
    breadcrumbs, fileCount, checkedFiles, checkedDirs, hasChecked,
    canGenerate, canFolders, canRename, canMoveMulti,
    setCat, enterDir, navRoot, navTo, navBack, loadFiles, applyRenameInPlace,
    applyFilter, sortLeft, toggleCheck, toggleAll, deleteFile, deleteSelected, getFileCat,
    fileDragStart, fileDragEnd, dropOnCat, dropOnFolder,
    setType, doSearch, pickTMDB, loadSeasons,
    showTooltipTmdb, moveTooltip, hideTooltip, autoSearch,
    doMatch, expandCheckedFolders, dropOnTmdb,
    startRename, execRename, dStart, dDrop, removeRight, clearRight,
    openMoveModal, openMoveModalMulti, closeMoveModal, execMove,
    suggestedMoveFolder, suggestedParentName,
    moveChangeCat, moveEnterFolder, moveNavTo, moveNavRoot, movePickFolder, movePickCurrent,
    createMoveFolder,
    openFolderModal, toggleAudioTag, toggleBatchAudioTag, updateFolderPreview, execFolderOrganize,
    execRenameAllFolders, autoDetectFolders, detectSeasonNum,
    openRenameFolderModal, execRenameFolder,
    refreshEmby, sanitize, cleanName, getGenreCategory,
    renameHistory, undoRename, clearRenameHistory,
    moveHistory, undoMove, clearMoveHistory, showMoveHistoryModal,
    namingIssues, analysisActive, analyzeNames, clearAnalysis, issuesCount,
    computeQualityScore, getQualityColor,
    renameProfiles, getAllProfiles, saveProfile, deleteProfile, applyProfile,
    anomalyRules, saveAnomalyRules, showAnomalyConfigModal,
    multiCatMode, toggleMultiCat, extractFromSubfolders, extractionRunning, cancelExtraction,
    isFileNew, newFilesCount,
    fileRenameStatus,
    thumbnailCache, loadThumbnail,
    moveConflicts, showMoveConflictModal, execMoveWithOverwrite, cancelMoveConflict,
    fileMetaModal, openFileMeta, closeFileMeta,
    renameErrors, showRenameErrorsModal, clearRenameErrors,
    fuzzyTmdbSearch,
    computeDiff,
    exportRenameCsv, importRenameCsv,
    customRules, addCustomRule, deleteCustomRule, applyCustomRules,
    releaseTags, releaseTagsDefaults, releaseTagsLoaded,
    loadReleaseTags, saveReleaseTags, resetReleaseTags,
    showAdvancedModal, advancedTab,
    crossCatDuplicates, checkingDuplicates, checkCrossCatDuplicates,
  }
}
