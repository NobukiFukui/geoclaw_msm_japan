% ======================================================================= 
% (function) resize_figure_window
% Nobuki Fukui, Kyoto University
% Description: figure window�̃T�C�Y��ς���
% ----------------------------------------------------------------------
% Syntax: resize_figure_window(nw,nh)
% Input: nw(���̐L�k��), nh(�����̐L�k��)
% ----------------------------------------------------------------------
% Update: 2019/3/11, v1, �쐬(�Q�l 
% https://hydrocoast.jp/index.php?MATLAB/Figure%E3%81%AE%E8%AA%BF%E6%95%B4) 
% ======================================================================

function resize_figure_window(nw,nh)

% �ő�T�C�Y�̎擾
scrsz = get(groot,'ScreenSize');
maxW = scrsz(3);
maxH = scrsz(4);

p = get(gcf,'Position');
dw = p(3)-min(nw*p(3),maxW);
dh = p(4)-min(nh*p(4),maxH);
set(gcf,'Position',[p(1)+dw/2  p(2)+dh  min(nw*p(3),maxW)  min(nh*p(4),maxH)])

end